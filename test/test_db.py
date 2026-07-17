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

from pychronicle.db import (
    init_db,
    insert_event,
    insert_events_batch,
    query_by_line,
    get_total_steps,
    get_event_at_step,
    get_all_variables_state_at_step,
)


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

    def test_batch_inserts_and_retrievals(self):
        # 1. Batch insertion with dicts and tuples
        events = [
            {"line_number": 10, "variable_name": "a", "serialized_value": "1"},
            (11, "b", "2"),
            {"line_number": 10, "variable_name": "a", "serialized_value": "3"}
        ]
        
        insert_events_batch(self.conn, events, session_id="session_1")
        
        # Verify total steps
        self.assertEqual(get_total_steps(self.conn, session_id="session_1"), 3)
        self.assertEqual(get_total_steps(self.conn, session_id="session_non_existent"), 0)
        
        # Verify query_by_line
        events_line_10 = query_by_line(self.conn, 10, session_id="session_1")
        self.assertEqual(len(events_line_10), 2)
        self.assertEqual(events_line_10[0]["variable_name"], "a")
        self.assertEqual(events_line_10[0]["serialized_value"], "1")
        self.assertEqual(events_line_10[1]["serialized_value"], "3")
        
        # Verify get_event_at_step
        event_0 = get_event_at_step(self.conn, 0, session_id="session_1")
        self.assertEqual(event_0["line_number"], 10)
        self.assertEqual(event_0["variable_name"], "a")
        self.assertEqual(event_0["serialized_value"], "1")
        
        event_1 = get_event_at_step(self.conn, 1, session_id="session_1")
        self.assertEqual(event_1["line_number"], 11)
        self.assertEqual(event_1["variable_name"], "b")
        self.assertEqual(event_1["serialized_value"], "2")
        
        event_none = get_event_at_step(self.conn, 99, session_id="session_1")
        self.assertIsNone(event_none)
        
        # Verify get_all_variables_state_at_step
        state_0 = get_all_variables_state_at_step(self.conn, 0, session_id="session_1")
        self.assertEqual(state_0, {"a": "1"})
        
        state_1 = get_all_variables_state_at_step(self.conn, 1, session_id="session_1")
        self.assertEqual(state_1, {"a": "1", "b": "2"})
        
        state_2 = get_all_variables_state_at_step(self.conn, 2, session_id="session_1")
        self.assertEqual(state_2, {"a": "3", "b": "2"})
        
        state_empty = get_all_variables_state_at_step(self.conn, 99, session_id="session_1")
        self.assertEqual(state_empty, {})


if __name__ == "__main__":
    unittest.main()
