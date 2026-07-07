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
    """Initializes the database and creates the events table."""
    db_dir = os.path.dirname(db_name)
    if db_dir and db_dir != ":memory:":
        os.makedirs(db_dir, exist_ok=True)

    conn = sqlite3.connect(db_name)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp       REAL    NOT NULL,
            line_number     INTEGER NOT NULL,
            variable_name   TEXT    NOT NULL,
            serialized_value TEXT   NOT NULL
        )
    """)
    conn.commit()
    return conn
