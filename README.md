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
