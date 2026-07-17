# PyChronicle
AST-Powered Time-Travel Debugger

## 📖 SQLite Storage Module

A robust SQLite-based events tracing database storage module. This component tracks, logs, and queries state transitions and variable changes during code execution, serving as the storage backend for **PyChronicle**.

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## 🚀 Overview

The Storage Module saves execution events to a local SQLite database (`trace.db`). It records:
- Precise timestamp of each event
- Line number where the execution event occurred
- Name of the variable being traced
- String representation of the variable's value at that line
- Session identifier to isolate traces from different runs

### Performance Optimizations
The module applies the following SQLite PRAGMAs for faster writes:
- **WAL journal mode** — enables concurrent reads during writes
- **NORMAL synchronous** — reduces disk sync overhead
- **MEMORY temp store** — keeps temp tables in RAM
- **20 MB cache size** — larger in-memory page cache

---

## 📦 Database Schema

All execution events are stored in the `events` table:

| Column | Data Type | Description |
| :--- | :--- | :--- |
| `id` | `INTEGER PRIMARY KEY AUTOINCREMENT` | Auto-incrementing unique identifier for each trace event. |
| `session_id` | `TEXT NOT NULL` | Identifier for the tracing session (isolates runs). |
| `timestamp` | `REAL NOT NULL` | Epoch timestamp (decimal float) of when the event was recorded. |
| `line_number` | `INTEGER NOT NULL` | The line number of the python file where the state changed. |
| `variable_name` | `TEXT NOT NULL` | The name of the variable tracked at that line. |
| `serialized_value` | `TEXT NOT NULL` | The string representation or serialized form of the variable's value. |

### Indexes
| Index | Columns | Purpose |
| :--- | :--- | :--- |
| `idx_events_session_line` | `(session_id, line_number)` | Fast lookup of events by line within a session. |
| `idx_events_session_step` | `(session_id, id)` | Efficient step-based replay queries. |

---

## 🔧 API Reference

The module exposes six main functions:

### 1. `init_db(db_name)`
Initializes the SQLite database connection, applies performance PRAGMAs, creates the `events` schema and indexes.
* **Arguments:** `db_name` (str) - Path to the database file (defaults to `data/trace.db`). Pass `":memory:"` to run in-memory.
* **Returns:** `sqlite3.Connection` object configured with `sqlite3.Row`.

```python
from pychronicle import init_db

# Connect to file-based database (creates dir/file automatically)
conn = init_db()

# Connect to in-memory database (great for tests)
memory_conn = init_db(":memory:")
```

### 2. `insert_event(conn, line_number, variable_name, serialized_value, session_id='default')`
Appends a single variable trace event to the storage backend.
* **Arguments:** 
  * `conn`: `sqlite3.Connection` database connection.
  * `line_number` (int): Line of the tracer change.
  * `variable_name` (str): Identifier of the traced variable.
  * `serialized_value` (str): String representation/serialized value of the variable.
  * `session_id` (str): Session identifier (defaults to `'default'`).
* **Returns:** `int` - The auto-generated row `id` of the inserted record.

```python
from pychronicle import insert_event

row_id = insert_event(conn, line_number=42, variable_name="user_role", serialized_value="'admin'")
print(f"Recorded event ID: {row_id}")
```

### 3. `insert_events_batch(conn, events, session_id='default')`
Inserts multiple events in a single transaction for high-performance bulk writes.
* **Arguments:**
  * `conn`: `sqlite3.Connection` database connection.
  * `events`: A list of dicts (`keys: line_number, variable_name, serialized_value, optional timestamp`) or a list of tuples `(line_number, variable_name, serialized_value)`.
  * `session_id` (str): Session identifier (defaults to `'default'`).

```python
from pychronicle import insert_events_batch

events = [
    {"line_number": 10, "variable_name": "x", "serialized_value": "1"},
    {"line_number": 11, "variable_name": "y", "serialized_value": "2"},
]
insert_events_batch(conn, events, session_id="run_001")

# Also supports tuples
insert_events_batch(conn, [(10, "x", "1"), (11, "y", "2")])
```

### 4. `query_by_line(conn, line_number, session_id='default')`
Retrieves all recorded events for a specific line number within a session.
* **Arguments:**
  * `conn`: `sqlite3.Connection` database connection.
  * `line_number` (int): The line number to filter by.
  * `session_id` (str): Session identifier (defaults to `'default'`).
* **Returns:** `list[dict]` - A list of dictionaries representing each event matching the line number, sorted by insertion order.

```python
from pychronicle import query_by_line

events = query_by_line(conn, line_number=42)
for event in events:
    print(f"Time: {event['timestamp']} | Var: {event['variable_name']} = {event['serialized_value']}")
```

### 5. `get_total_steps(conn, session_id='default')`
Returns the total number of events recorded in a session. Useful for building the step slider in the UI.
* **Arguments:**
  * `conn`: `sqlite3.Connection` database connection.
  * `session_id` (str): Session identifier (defaults to `'default'`).
* **Returns:** `int` - Total count of events.

```python
from pychronicle import get_total_steps

total = get_total_steps(conn, session_id="run_001")
print(f"Total execution steps: {total}")
```

### 6. `get_event_at_step(conn, step_index, session_id='default')`
Fetches the event at a specific 0-based step index in the session (ordered by insertion order). Powers step-by-step replay.
* **Arguments:**
  * `conn`: `sqlite3.Connection` database connection.
  * `step_index` (int): 0-based step position.
  * `session_id` (str): Session identifier (defaults to `'default'`).
* **Returns:** `dict | None` - The event dictionary, or `None` if the step is out of range.

```python
from pychronicle import get_event_at_step

event = get_event_at_step(conn, step_index=0, session_id="run_001")
print(f"Step 0: Line {event['line_number']} | {event['variable_name']} = {event['serialized_value']}")
```

### 7. `get_all_variables_state_at_step(conn, step_index, session_id='default')`
Compiles a snapshot of all variable values at a given step. Returns the most recent value of each variable up to and including the specified step.
* **Arguments:**
  * `conn`: `sqlite3.Connection` database connection.
  * `step_index` (int): 0-based step position.
  * `session_id` (str): Session identifier (defaults to `'default'`).
* **Returns:** `dict` - Mapping of `variable_name` → `serialized_value`.

```python
from pychronicle import get_all_variables_state_at_step

state = get_all_variables_state_at_step(conn, step_index=5, session_id="run_001")
for var, val in state.items():
    print(f"  {var} = {val}")
```

---

## 🧪 Testing & Validation

The database module includes a self-contained test suite that validates all functionality against an in-memory SQLite instance.

To run the unit tests, use python unittest runner:

```bash
python -m unittest test.test_db -v
```

### Expected Output:
```text
test_init_db (test.test_db.TestStorageDB) ... ok
test_insert_and_query_events (test.test_db.TestStorageDB) ... ok
test_insert_events_batch (test.test_db.TestStorageDB) ... ok
test_get_total_steps (test.test_db.TestStorageDB) ... ok
test_get_event_at_step (test.test_db.TestStorageDB) ... ok
test_get_all_variables_state_at_step (test.test_db.TestStorageDB) ... ok

----------------------------------------------------------------------
Ran 6 tests in 0.005s

OK
```

---

## 📁 Project Structure

```text
├── data/                   # Auto-generated database storage directory
│   └── trace.db            # SQLite database file
├── pychronicle/            # Core debugger engine package
│   ├── __init__.py         # Package exports
│   ├── ast_parser.py       # AST parsing logic (P1)
│   ├── hook_injector.py    # AST rewrite hooks (P1)
│   └── db.py               # SQLite storage module (P3 - Pankaj)
├── test/                   # Unit test suites
│   ├── test_ast_parser.py  # AST parser tests
│   ├── test_db.py          # Database unit tests (P3 - Pankaj)
│   └── storage_audit.py    # Storage audit script (P3 - Pankaj)
└── README.md               # Project documentation (this file)
```
