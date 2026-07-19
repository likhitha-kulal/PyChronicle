"""
PyChronicle Tracer Module.

Implements program execution tracing using:

1. sys.settrace() for line-by-line execution tracking.
2. AST hook injection for variable assignment monitoring.
3. SQLite event storage for captured trace data.

Supports reusable Tracer class usage and command-line execution
for tracing Python programs.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys

from pychronicle.db import init_db, insert_event
from pychronicle.hook_injector import inject_hooks

DEFAULT_TARGET = "test/fixtures/test_target.py"

REPR_MAX_LEN = 500

logger = logging.getLogger("pychronicle.tracer")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(_handler)
logger.setLevel(logging.INFO)


class Tracer:
    """Reusable execution tracer for Python programs."""

    def __init__(self, target_file: str):
        if not os.path.isfile(target_file):
            raise FileNotFoundError(
                f"Tracer target does not exist or is not a file: {target_file!r}"
            )

        self.target_file = os.path.abspath(target_file)
        self.conn = None

    def trace_callback(self, frame, event, arg):
        """
        Trace callback used by sys.settrace().

        Responsible only for execution tracing.
        Variable changes are handled by the injected AST hooks.
        """

        # Prune frames outside the target file immediately, so Python
        # stops invoking this callback for their sub-events entirely.
        if os.path.abspath(frame.f_code.co_filename) != self.target_file:
            return None

        if event != "line":
            return self.trace_callback

        locals_dict = {
            key: value
            for key, value in frame.f_locals.items()
            if not (key.startswith("__") and key.endswith("__"))
        }

        logger.info(
            "Line %s | Event: %s | Locals: %s",
            frame.f_lineno,
            event,
            locals_dict,
        )

        return self.trace_callback

    def hook(self, var_name, value, lineno):
        """
        Called by injected AST hooks whenever a variable assignment occurs.

        Any failure here (bad __repr__, DB error, etc.) is caught and
        logged rather than allowed to propagate into the traced program,
        since a tracer-internal problem should never crash the target.
        """

        try:
            value_repr = repr(value)
        except Exception as exc:  # noqa: BLE001 - repr can raise arbitrary errors
            value_repr = f"<unrepresentable: {exc!r}>"

        if len(value_repr) > REPR_MAX_LEN:
            value_repr = value_repr[:REPR_MAX_LEN] + "...<truncated>"

        logger.info("[HOOK] Line %s | %s = %s", lineno, var_name, value_repr)

        if self.conn is None:
            logger.warning(
                "[HOOK] Skipping DB write for %s at line %s: no active connection",
                var_name,
                lineno,
            )
            return

        try:
            insert_event(self.conn, lineno, var_name, value_repr)
        except Exception:
            logger.exception(
                "[HOOK] Failed to record event for %s at line %s", var_name, lineno
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
                self.conn = None


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


def main() -> int:
    """Command-line entry point. Returns a process exit code."""

    parser = argparse.ArgumentParser(
        description="Run the PyChronicle tracer."
    )

    parser.add_argument(
        "target",
        nargs="?",
        default=DEFAULT_TARGET,
        help="Python file to trace",
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    target = resolve_target_file(args.target)

    try:
        tracer = Tracer(target)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    try:
        tracer.run()
    except Exception:
        logger.exception("Tracing target %s failed", target)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())