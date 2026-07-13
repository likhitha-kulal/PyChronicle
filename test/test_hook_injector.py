"""
test_hook_injector.py - unit tests for pychronicle.hook_injector

Run with:
    pytest test/test_hook_injector.py -v
    or
    python -m pytest test/test_hook_injector.py -v

    python -m pytest test/ -v(all old +new tests)
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pychronicle.hook_injector import inject_hooks, HookInjector

FIXTURE_PATH = os.path.join(
    os.path.dirname(__file__), "fixtures", "test_target.py"
)


def _run(source: str) -> list[tuple]:
    """Helper: inject hooks into source string, exec it, return captured log."""
    log = []
    rewritten = inject_hooks(source)
    code = compile(rewritten, "<test>", "exec")
    exec(code, {"__pychronicle_hook__": lambda n, v, l: log.append((n, v, l))})
    return log


class TestInjectHooks(unittest.TestCase):

    def test_rewritten_source_compiles(self):
        """inject_hooks() output must compile without errors — tests the
        location fix from Day 3."""
        source = open(FIXTURE_PATH).read()
        rewritten = inject_hooks(source)
        try:
            compile(rewritten, FIXTURE_PATH, "exec")
        except (SyntaxError, ValueError) as e:
            self.fail(f"Rewritten source failed to compile: {e}")

    def test_hook_fires_for_simple_assignment(self):
        log = _run("x = 42\n")
        self.assertEqual(len(log), 1)
        self.assertEqual(log[0], ("x", 42, 1))

    def test_hook_fires_every_iteration_of_loop(self):
        """Critical: must fire once per iteration, not once total."""
        log = _run("for i in range(5):\n    x = i * 2\n")
        x_entries = [(n, v, l) for n, v, l in log if n == "x"]
        self.assertEqual(len(x_entries), 5)
        self.assertEqual([v for _, v, _ in x_entries], [0, 2, 4, 6, 8])

    def test_hook_fires_for_tuple_unpacking(self):
        log = _run("a, b = 10, 20\n")
        names = {n for n, v, l in log}
        self.assertIn("a", names)
        self.assertIn("b", names)
        values = {n: v for n, v, l in log}
        self.assertEqual(values["a"], 10)
        self.assertEqual(values["b"], 20)

    def test_hook_fires_for_chained_assignment(self):
        log = _run("c = d = 99\n")
        names = {n for n, v, l in log}
        self.assertIn("c", names)
        self.assertIn("d", names)

    def test_subscript_does_not_fire_hook(self):
        log = _run("items = [1, 2, 3]\nitems[0] = 99\n")
        # hook fires for `items = [1,2,3]` but NOT for `items[0] = 99`
        self.assertEqual(len(log), 1)
        self.assertEqual(log[0][0], "items")

    def test_lineno_in_hook_matches_source(self):
        """Line number passed to hook must match where the assignment is."""
        source = "x = 1\ny = 2\nz = 3\n"
        log = _run(source)
        line_map = {n: l for n, v, l in log}
        self.assertEqual(line_map["x"], 1)
        self.assertEqual(line_map["y"], 2)
        self.assertEqual(line_map["z"], 3)

    def test_full_fixture_executes_correctly(self):
        """Runs the full shared fixture through injection — integration smoke test."""
        source = open(FIXTURE_PATH).read()
        log = _run(source)
        names_captured = {n for n, v, l in log}
        for expected in ["total", "squared", "x", "y", "a", "b", "items"]:
            self.assertIn(expected, names_captured, f"Missing: {expected}")


if __name__ == "__main__":
    unittest.main()