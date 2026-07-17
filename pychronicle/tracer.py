"""
Tracer Module for PyChronicle.

Uses both:
1. sys.settrace() for line-by-line execution tracing.
2. P1's AST hook injector for assignment hooks.

Stores traced events in the SQLite database.
"""

from __future__ import annotations

import os
import sys

# Allow imports when running:
# python pychronicle/tracer.py
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)

from pychronicle.db import init_db, insert_event
from pychronicle.hook_injector import inject_hooks


DEFAULT_TARGET = "test/fixtures/test_target.py"

if len(sys.argv) > 1:
    target = sys.argv[1]

    if os.path.exists(target):
        TARGET_FILE = os.path.abspath(target)
    else:
        TARGET_FILE = os.path.abspath(
            os.path.join("test", "fixtures", target)
        )
else:
    TARGET_FILE = os.path.abspath(DEFAULT_TARGET)


conn = init_db()


def trace_callback(frame, event, arg):
    """
    Line-by-line tracer using sys.settrace().

    Responsible only for execution tracing.
    Variable changes are captured by AST hooks.
    """

    if os.path.abspath(frame.f_code.co_filename) != TARGET_FILE:
        return trace_callback

    if event != "line":
        return trace_callback

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

    # Do NOT insert variable events here.
    # P1 AST hooks handle variable changes.

    return trace_callback


def __pychronicle_hook__(var_name, value, lineno):
    """
    Called by P1's injected hooks.

    This is the single source of variable change events.
    """

    print(
        f"[HOOK] Line {lineno} | "
        f"{var_name} = {value}"
    )

    insert_event(
        conn,
        lineno,
        var_name,
        repr(value),
    )


with open(TARGET_FILE, "r", encoding="utf-8") as f:
    source = f.read()


# Rewrite source using P1's injector
rewritten_source = inject_hooks(source)

# Compile rewritten source
code = compile(
    rewritten_source,
    TARGET_FILE,
    "exec"
)


exec_globals = {
    "__name__": "__main__",
    "__file__": TARGET_FILE,
    "__pychronicle_hook__": __pychronicle_hook__,
}


sys.settrace(trace_callback)

try:
    exec(code, exec_globals)
finally:
    sys.settrace(None)
    conn.close()