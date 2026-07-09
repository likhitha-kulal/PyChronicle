import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pychronicle.hook_injector import inject_hooks


class TestHookInjector(unittest.TestCase):
    def _run(self, source):
        """Helper: inject hooks into source, exec it, return captured log."""
        log = []
        rewritten = inject_hooks(source)
        exec(
            rewritten,
            {"__pychronicle_hook__": lambda n, v, l: log.append((n, v, l))},
        )
        return log

    def test_hook_fires_for_simple_assignment(self):
        log = self._run("x = 42\n")
        self.assertEqual(log, [("x", 42, 1)])

    def test_hook_fires_every_iteration_of_loop(self):
        """Critical: hook must fire once per loop iteration, not just once."""
        log = self._run("for i in range(3):\n    x = i\n")
        self.assertEqual(len(log), 3)
        self.assertEqual([v for _, v, _ in log], [0, 1, 2])

    def test_rewritten_source_is_valid_python(self):
        """inject_hooks() output must compile without errors."""
        source = "a, b = 1, 2\nc = a + b\n"
        rewritten = inject_hooks(source)
        try:
            compile(rewritten, "<test>", "exec")
        except SyntaxError as e:
            self.fail(f"Rewritten source has SyntaxError: {e}")


if __name__ == "__main__":
    unittest.main()
