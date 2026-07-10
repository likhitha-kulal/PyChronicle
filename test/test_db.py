"""
test_db.py — unit tests for pychronicle.db

Owner: P3 (Storage Engineer)
Week: 1
"""

import os
import sys
import unittest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)

from pychronicle.db import init_db, insert_event, query_by_line


class TestStorageDB(unittest.TestCase):
    def setUp(self):
        self.conn = init_db(":memory:")

    def tearDown(self):
        self.conn.close()

    def test_init_db(self):
        # Verify events table exists
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='events'")
        table = cursor.fetchone()
        self.assertIsNotNone(table)

    def test_insert_and_query_events(self):
        row_id1 = insert_event(self.conn, 3, "x", "10")
        row_id2 = insert_event(self.conn, 3, "x", "20")
        row_id3 = insert_event(self.conn, 5, "y", "'hello'")

        self.assertEqual(row_id1, 1)
        self.assertEqual(row_id2, 2)
        self.assertEqual(row_id3, 3)

        # Query line 3
        events_3 = query_by_line(self.conn, 3)
        self.assertEqual(len(events_3), 2)
        self.assertEqual(events_3[0]["variable_name"], "x")
        self.assertEqual(events_3[0]["serialized_value"], "10")
        self.assertEqual(events_3[1]["serialized_value"], "20")

        # Query line 5
        events_5 = query_by_line(self.conn, 5)
        self.assertEqual(len(events_5), 1)
        self.assertEqual(events_5[0]["variable_name"], "y")
        self.assertEqual(events_5[0]["serialized_value"], "'hello'")

        # Query non-existent line
        events_empty = query_by_line(self.conn, 999)
        self.assertEqual(len(events_empty), 0)


if __name__ == "__main__":
    unittest.main()
