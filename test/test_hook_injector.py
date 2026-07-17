"""
test_hook_injector.py — P1, Weeks 2-3 test suite.
Owner: P1

Week 2: 8 tests covering visit_Assign (basic, loop, tuple, chained, etc.)
Week 3: 3 new tests added (Day 1) — one per new visitor method

Run with:
    pytest test/test_hook_injector.py -v

Total expected: 11 tests, all passing.
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pychronicle.hook_injector import inject_hooks

FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "test_target.py"
)


def _run(source: str) -> list[tuple]:
    """
    Helper: inject hooks into source string, exec it, return captured log.
    Each entry in log is (var_name, value, lineno).
    """
    log = []
    rewritten = inject_hooks(source)
    code = compile(rewritten, "<test>", "exec")
    exec(code, {"__pychronicle_hook__": lambda n, v, l: log.append((n, v, l))})
    return log


# ══════════════════════════════════════════════════════════════════════
# Week 2 tests — visit_Assign (all must still pass in Week 3)
# ══════════════════════════════════════════════════════════════════════

class TestVisitAssign(unittest.TestCase):
    """Week 2 tests — must all stay passing through Week 3 and beyond."""

    def test_rewritten_source_compiles(self):
        """
        inject_hooks() output must compile without ValueError.
        This test specifically catches the location bug fixed in
        Week 2 Day 3: _make_call() must copy location from the real
        anchor node, not self-referentially from call.value.
        """
        source = open(FIXTURE).read()
        rewritten = inject_hooks(source)
        try:
            compile(rewritten, FIXTURE, "exec")
        except (SyntaxError, ValueError) as e:
            self.fail(f"Rewritten source failed to compile: {e}")

    def test_simple_assignment(self):
        log = _run("x = 42\n")
        self.assertEqual(log, [("x", 42, 1)])

    def test_hook_fires_every_loop_iteration(self):
        """
        Core regression test: hook must fire once per iteration,
        not just once for the whole loop.
        """
        log = _run("for i in range(5):\n    x = i * 2\n")
        x_vals = [v for n, v, l in log if n == "x"]
        self.assertEqual(x_vals, [0, 2, 4, 6, 8])

    def test_tuple_unpacking(self):
        log = _run("a, b = 10, 20\n")
        vals = {n: v for n, v, l in log}
        self.assertEqual(vals.get("a"), 10)
        self.assertEqual(vals.get("b"), 20)

    def test_chained_assignment(self):
        log = _run("c = d = 99\n")
        names = {n for n, v, l in log}
        self.assertIn("c", names)
        self.assertIn("d", names)

    def test_subscript_does_not_trigger_hook(self):
        """items[0] = 99 is a Subscript — must NOT produce a hook call."""
        log = _run("items = [1, 2, 3]\nitems[0] = 99\n")
        # Only items=[1,2,3] is captured. items[0]=99 produces nothing.
        self.assertEqual(len(log), 1)
        self.assertEqual(log[0][0], "items")

    def test_lineno_matches_source(self):
        """Line numbers in hook calls must match the original source."""
        log = _run("x = 1\ny = 2\nz = 3\n")
        line_map = {n: l for n, v, l in log}
        self.assertEqual(line_map["x"], 1)
        self.assertEqual(line_map["y"], 2)
        self.assertEqual(line_map["z"], 3)

    def test_full_fixture_captures_all_variables(self):
        """Smoke test: run the shared fixture, all expected vars appear."""
        log = _run(open(FIXTURE).read())
        names = {n for n, v, l in log}
        for expected in ["total", "squared", "x", "y", "a", "b", "items"]:
            self.assertIn(expected, names, f"Missing variable: {expected}")


# ══════════════════════════════════════════════════════════════════════
# Week 3 tests — 3 new visitor methods (added Day 1)
# ══════════════════════════════════════════════════════════════════════

class TestVisitAugAssign(unittest.TestCase):
    """
    Week 3 Addition 1: visit_AugAssign handles x += 1, x -= 2 etc.

    Why this was missing before:
        ast.AugAssign is a different node type from ast.Assign.
        Python never calls visit_Assign for augmented assignments.
        Without visit_AugAssign, x += 1 produced no hook call at all.

    Key field difference from ast.Assign:
        node.target  singular (not node.targets list)
        node.op      the operator: Add, Sub, Mult, Div ...
    """

    def test_aug_assign_basic(self):
        """x += 1 must produce a hook call after the augmented assign."""
        log = _run("x = 0\nx += 5\n")
        x_vals = [v for n, v, l in log if n == "x"]
        # x=0 captured by visit_Assign, x=5 captured by visit_AugAssign
        self.assertEqual(x_vals, [0, 5])

    def test_aug_assign_multiple_operators(self):
        """All augmented operator variants must be captured."""
        log = _run("x = 10\nx -= 3\nx *= 2\nx //= 5\n")
        x_vals = [v for n, v, l in log if n == "x"]
        # 10, then 10-3=7, then 7*2=14, then 14//5=2
        self.assertEqual(x_vals, [10, 7, 14, 2])

    def test_aug_assign_in_loop(self):
        """
        Augmented assignment inside a loop must fire every iteration.
        This is the most important AugAssign case — accumulator patterns.
        """
        log = _run("total = 0\nfor i in range(5):\n    total += i\n")
        total_vals = [v for n, v, l in log if n == "total"]
        # total=0, then 0, 1, 3, 6, 10 (one per iteration)
        self.assertEqual(total_vals, [0, 0, 1, 3, 6, 10])


class TestVisitAnnAssign(unittest.TestCase):
    """
    Week 3 Addition 2: visit_AnnAssign handles x: int = 5.

    Why this was missing before:
        ast.AnnAssign is a separate node type. The annotation (: int)
        makes Python parse it differently from a plain assignment.

    Critical rule:
        node.value can be None for bare declarations (x: int).
        Those must NOT produce a hook — there is no value to capture.
    """

    def test_ann_assign_with_value(self):
        """x: int = 42 has a value — hook must fire."""
        log = _run("x: int = 42\n")
        self.assertEqual(len(log), 1)
        self.assertEqual(log[0], ("x", 42, 1))

    def test_ann_assign_bare_declaration_skipped(self):
        """
        x: int with NO value must NOT produce a hook call.
        node.value is None in this case — nothing was assigned.
        """
        log = _run("x: int\n")
        self.assertEqual(log, [], "Bare declaration must not trigger hook")

    def test_ann_assign_mixed(self):
        """Mix of bare declarations and real assignments."""
        log = _run("x: int\ny: str = 'hello'\nz: float\nw: bool = True\n")
        names = {n for n, v, l in log}
        # Only y and w have values — x and z are bare
        self.assertIn("y", names)
        self.assertIn("w", names)
        self.assertNotIn("x", names)
        self.assertNotIn("z", names)


class TestVisitFor(unittest.TestCase):
    """
    Week 3 Addition 3: visit_For captures the loop variable.

    Why this was missing before:
        `for i in range(n):` does NOT create an ast.Assign node.
        The variable i is bound by the For node's .target field.
        visit_Assign never fires for it so i was completely invisible.

    Strategy: prepend hook as FIRST statement inside the loop body.
    This fires right after Python binds i for each iteration.
    """

    def test_for_loop_variable_captured(self):
        """i must be captured once per iteration, in correct order."""
        log = _run("for i in range(3):\n    pass\n")
        i_vals = [v for n, v, l in log if n == "i"]
        self.assertEqual(i_vals, [0, 1, 2])

    def test_for_loop_captures_before_body(self):
        """
        Hook for i must fire BEFORE the body's assignments.
        If we appended instead of prepended, i would be captured
        after x, giving wrong ordering.
        """
        log = _run("for i in range(2):\n    x = i * 10\n")
        # Expected order: i=0, x=0, i=1, x=10
        pairs = [(n, v) for n, v, l in log]
        self.assertEqual(pairs[0], ("i", 0))   # i first
        self.assertEqual(pairs[1], ("x", 0))   # then x
        self.assertEqual(pairs[2], ("i", 1))   # then next i
        self.assertEqual(pairs[3], ("x", 10))  # then next x

    def test_for_loop_nested(self):
        """Nested for loops — both loop variables captured."""
        log = _run(
            "for i in range(2):\n"
            "    for j in range(2):\n"
            "        pass\n"
        )
        i_vals = [v for n, v, l in log if n == "i"]
        j_vals = [v for n, v, l in log if n == "j"]
        self.assertEqual(i_vals, [0, 1])
        # j cycles 0,1 for each i: [0,1,0,1]
        self.assertEqual(j_vals, [0, 1, 0, 1])


if __name__ == "__main__":
    unittest.main()