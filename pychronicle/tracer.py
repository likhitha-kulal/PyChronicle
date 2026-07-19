"""
Tracer module for PyChronicle.

Provides a reusable Tracer class that combines:

1. sys.settrace() for execution tracing.
2. AST hook injection for variable assignment tracking.

Can be imported by other modules or executed directly.
"""

from __future__ import annotations

import argparse
import os
import sys

from pychronicle.db import init_db, insert_event
from pychronicle.hook_injector import inject_hooks

DEFAULT_TARGET = "test/fixtures/test_target.py"


class Tracer:
    """Reusable execution tracer for Python programs."""

    def __init__(self, target_file: str):
        self.target_file = os.path.abspath(target_file)
        self.conn = None

    def trace_callback(self, frame, event, arg):
        """
        Trace callback used by sys.settrace().

        Responsible only for execution tracing.
        Variable changes are handled by the injected AST hooks.
        """

        if os.path.abspath(frame.f_code.co_filename) != self.target_file:
            return self.trace_callback

        if event != "line":
            return self.trace_callback

        ignore = {
            "__builtins__",
            "__name__",
            "__file__",
            "__doc__",
            "__package__",
            "__loader__",
            "__spec__",
            "__cached__",
            "__pychronicle_hook__",
        }

        locals_dict = {
            key: value
            for key, value in frame.f_locals.items()
            if key not in ignore
        }

        print(
            f"Line {frame.f_lineno} | "
            f"Event: {event} | "
            f"Locals: {locals_dict}"
        )

        return self.trace_callback

    def hook(self, var_name, value, lineno):
        """
        Called by injected AST hooks whenever
        a variable assignment occurs.
        """

        print(
            f"[HOOK] Line {lineno} | "
            f"{var_name} = {value}"
        )

        insert_event(
            self.conn,
            lineno,
            var_name,
            repr(value),
        )

    def run(self):
        """Execute tracing."""

        self.conn = init_db()

        try:
            with open(self.target_file, "r", encoding="utf-8") as file:
                source = file.read()

            rewritten_source = inject_hooks(source)

            code = compile(
                rewritten_source,
                self.target_file,
                "exec",
            )

            exec_globals = {
                "__name__": "__main__",
                "__file__": self.target_file,
                "__pychronicle_hook__": self.hook,
            }

            sys.settrace(self.trace_callback)

            try:
                exec(code, exec_globals)
            finally:
                sys.settrace(None)

        finally:
            if self.conn is not None:
                self.conn.close()


def resolve_target_file(target: str | None = None) -> str:
    """
    Resolve the target file to trace.
    """

    if target is None:
        return os.path.abspath(DEFAULT_TARGET)

    if os.path.exists(target):
        return os.path.abspath(target)

    return os.path.abspath(
        os.path.join("test", "fixtures", target)
    )


def main():
    """Command-line entry point."""

    parser = argparse.ArgumentParser(
        description="Run the PyChronicle tracer."
    )

    parser.add_argument(
        "target",
        nargs="?",
        default=DEFAULT_TARGET,
        help="Python file to trace",
    )

    args = parser.parse_args()

    target = resolve_target_file(args.target)

    tracer = Tracer(target)
    tracer.run()


if __name__ == "__main__":
    main()