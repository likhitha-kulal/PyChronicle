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
