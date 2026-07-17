"""
SQLite Storage Module for PyChronicle.
Stores traced execution events in a local SQLite database.
"""

import sqlite3
import time
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data")
DB_NAME = os.path.join(DATA_DIR, "trace.db")


def init_db(db_name=DB_NAME):
    """Initializes the database, creates the events table and indexes, and applies PRAGMAs."""
    db_dir = os.path.dirname(db_name)
    if db_dir and db_dir != ":memory:":
        os.makedirs(db_dir, exist_ok=True)

    conn = sqlite3.connect(db_name)
    conn.row_factory = sqlite3.Row
    
    # Performance tuning PRAGMAs
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA temp_store = MEMORY;")
    conn.execute("PRAGMA cache_size = -20000;")  # ~20MB cache size
    
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id      TEXT    NOT NULL,
            timestamp       REAL    NOT NULL,
            line_number     INTEGER NOT NULL,
            variable_name   TEXT    NOT NULL,
            serialized_value TEXT   NOT NULL
        )
    """)
    
    # Create indexes for optimized queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_events_session_line 
        ON events (session_id, line_number)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_events_session_step 
        ON events (session_id, id)
    """)
    
    conn.commit()
    return conn


def insert_event(conn, line_number, variable_name, serialized_value, session_id='default'):
    """Inserts a new event into the events table."""
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO events (session_id, timestamp, line_number, variable_name, serialized_value)
        VALUES (?, ?, ?, ?, ?)
        """,
        (session_id, time.time(), line_number, variable_name, serialized_value),
    )
    conn.commit()
    return cursor.lastrowid


def insert_events_batch(conn, events, session_id='default'):
    """
    Inserts multiple events in a single transaction.
    
    Args:
        conn: The SQLite connection.
        events: A list of dicts (keys: line_number, variable_name, serialized_value, and optional timestamp)
                or a list of tuples (line_number, variable_name, serialized_value).
        session_id: The identifier for the tracing session.
    """
    cursor = conn.cursor()
    now = time.time()
    records = []
    for e in events:
        if isinstance(e, dict):
            records.append((
                session_id,
                e.get('timestamp', now),
                e['line_number'],
                e['variable_name'],
                e['serialized_value']
            ))
        else:
            # Tuple: (line_number, variable_name, serialized_value)
            records.append((session_id, now, e[0], e[1], e[2]))
            
    cursor.executemany(
        """
        INSERT INTO events (session_id, timestamp, line_number, variable_name, serialized_value)
        VALUES (?, ?, ?, ?, ?)
        """,
        records
    )
    conn.commit()


def query_by_line(conn, line_number, session_id='default'):
    """Queries and returns all events for a specific line number within a session."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, session_id, timestamp, line_number, variable_name, serialized_value
        FROM events
        WHERE session_id = ? AND line_number = ?
        ORDER BY id
        """,
        (session_id, line_number),
    )
    rows = cursor.fetchall()
    return [dict(row) for row in rows]


def get_total_steps(conn, session_id='default'):
    """Returns the total number of events recorded in a session."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM events WHERE session_id = ?",
        (session_id,)
    )
    res = cursor.fetchone()
    return res[0] if res else 0


def get_event_at_step(conn, step_index, session_id='default'):
    """
    Fetches the event at a specific 0-based step index in the session
    (ordered by id/timestamp).
    """
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, session_id, timestamp, line_number, variable_name, serialized_value
        FROM events
        WHERE session_id = ?
        ORDER BY id ASC
        LIMIT 1 OFFSET ?
        """,
        (session_id, step_index)
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def get_all_variables_state_at_step(conn, step_index, session_id='default'):
    """
    Compiles the state of all variables at a given 0-based step index
    in the session. Returns a dictionary mapping variable_name -> serialized_value.
    """
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id FROM events
        WHERE session_id = ?
        ORDER BY id ASC
        LIMIT 1 OFFSET ?
        """,
        (session_id, step_index)
    )
    row = cursor.fetchone()
    if not row:
        return {}
    target_id = row['id']
    
    cursor.execute(
        """
        SELECT variable_name, serialized_value, MAX(id)
        FROM events
        WHERE session_id = ? AND id <= ?
        GROUP BY variable_name
        """,
        (session_id, target_id)
    )
    rows = cursor.fetchall()
    
    state = {}
    for r in rows:
        state[r['variable_name']] = r['serialized_value']
    return state

