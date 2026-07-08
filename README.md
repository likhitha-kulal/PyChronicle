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

---

## 📦 Database Schema

All execution events are stored in the `events` table:

| Column | Data Type | Description |
| :--- | :--- | :--- |
| `id` | `INTEGER PRIMARY KEY AUTOINCREMENT` | Auto-incrementing unique identifier for each trace event. |
| `timestamp` | `REAL NOT NULL` | Epoch timestamp (decimal float) of when the event was recorded. |
| `line_number` | `INTEGER NOT NULL` | The line number of the python file where the state changed. |
| `variable_name` | `TEXT NOT NULL` | The name of the variable tracked at that line. |
| `serialized_value` | `TEXT NOT NULL` | The string representation or serialized form of the variable's value. |

---

## 🔧 API Reference

The module exposes three main functions:

### 1. `init_db(db_name)`
Initializes the SQLite database connection, creates parent folders if necessary, and builds the `events` schema.
* **Arguments:** `db_name` (str) - Path to the database file (defaults to `data/trace.db`). Pass `":memory:"` to run in-memory.
* **Returns:** `sqlite3.Connection` object configured with `sqlite3.Row`.

```python
from pychronicle import init_db

# Connect to file-based database (creates dir/file automatically)
conn = init_db()

# Connect to in-memory database (great for tests)
memory_conn = init_db(":memory:")
```

### 2. `insert_event(conn, line_number, variable_name, serialized_value)`
Appends a variable trace event to the storage backend.
* **Arguments:** 
  * `conn`: `sqlite3.Connection` database connection.
  * `line_number` (int): Line of the tracer change.
  * `variable_name` (str): Identifier of the traced variable.
  * `serialized_value` (str): String representation/serialized value of the variable.
* **Returns:** `int` - The auto-generated row `id` of the inserted record.

```python
from pychronicle import insert_event

row_id = insert_event(conn, line_number=42, variable_name="user_role", serialized_value="'admin'")
print(f"Recorded event ID: {row_id}")
```
