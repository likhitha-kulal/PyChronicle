"""
test_ast_parser.py — unit tests for pychronicle.ast_parser

Owner: P1 (AST Engineer)
Week: 1 (Day 4-5 deliverable)

Run with:
    pytest tests/test_ast_parser.py -v
or, if pytest isn't installed yet:
    python -m unittest tests.test_ast_parser -v
"""

from __future__ import annotations

import os
import sys
import unittest

# Make the package importable when running this file directly,
# without requiring `pip install -e .` yet.
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)

from pychronicle.ast_parser import find_assignments  # noqa: E402

FIXTURE_PATH = os.path.join(
    os.path.dirname(__file__), "fixtures", "test_target.py"
)


class TestFindAssignments(unittest.TestCase):
    def test_matches_known_fixture(self):
        """
        Core Week 1 test: find_assignments() on the shared fixture
        must return exactly the expected set of (line, name) pairs,
        documented in tests/fixtures/test_target.py's docstring.
        """
        expected = {
            (45, "x"),
            (46, "y"),
            (48, "a"),
            (48, "b"),
            (50, "c"),
            (50, "d"),
            (52, "items"),
            (38, "total"),
            (40, "total"),
            (41, "squared"),
        }
        actual = set(find_assignments(FIXTURE_PATH))
        self.assertEqual(actual, expected)

    def test_subscript_assignment_is_skipped(self):
        """
        items[0] = 99 (line 47 of the fixture) must NOT appear in the
        results — only plain Name targets are captured.
        """
        actual = find_assignments(FIXTURE_PATH)
        names_only = {name for _, name in actual}
        # 'items' (the list itself, line 46) is captured;
        # there should be no entry tied to a subscript expression.
        self.assertIn("items", names_only)
        self.assertEqual(
            sum(1 for line, name in actual if name == "items"), 1
        )

    def test_plain_assignment(self):
        """Sanity check on a minimal inline script via a temp file."""
        import tempfile

        source = "a = 1\nb = 2\n"
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as f:
            f.write(source)
            temp_path = f.name

        try:
            result = find_assignments(temp_path)
            self.assertEqual(result, [(1, "a"), (2, "b")])
        finally:
            os.remove(temp_path)

    def test_tuple_unpacking(self):
        """a, b = 1, 2 should yield two separate entries on the same line."""
        import tempfile

        source = "a, b = 1, 2\n"
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as f:
            f.write(source)
            temp_path = f.name

        try:
            result = find_assignments(temp_path)
            self.assertEqual(set(result), {(1, "a"), (1, "b")})
        finally:
            os.remove(temp_path)

    def test_chained_assignment(self):
        """c = d = 10 should yield two separate entries on the same line."""
        import tempfile

        source = "c = d = 10\n"
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as f:
            f.write(source)
            temp_path = f.name

        try:
            result = find_assignments(temp_path)
            self.assertEqual(set(result), {(1, "c"), (1, "d")})
        finally:
            os.remove(temp_path)

    def test_empty_file_returns_empty_list(self):
        import tempfile

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as f:
            f.write("")
            temp_path = f.name

        try:
            result = find_assignments(temp_path)
            self.assertEqual(result, [])
        finally:
            os.remove(temp_path)

    def test_no_assignments_returns_empty_list(self):
        """A file with only function defs/calls, no assignments."""
        import tempfile

        source = "def greet():\n    print('hello')\n\ngreet()\n"
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as f:
            f.write(source)
            temp_path = f.name

        try:
            result = find_assignments(temp_path)
            self.assertEqual(result, [])
        finally:
            os.remove(temp_path)


if __name__ == "__main__":
    unittest.main()