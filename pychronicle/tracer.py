"""
Tracer Module for PyChronicle.

Tracks Python program execution using sys.settrace(),
detects variable changes, and stores execution events
in the SQLite database.
"""

import sys
import os

# Allow imports when running: python pychronicle/tracer.py
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)

from pychronicle.db import init_db, insert_event

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

# Initialize database
conn = init_db()

# Store previous variable values
previous_locals = {}


def trace_callback(frame, event, arg):
    global previous_locals

    # Trace only the selected target file
    if os.path.abspath(frame.f_code.co_filename) != TARGET_FILE:
        return trace_callback

    # Only process executed lines
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
        "compute",
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

    # Store only variables whose value changed
    for variable_name, variable_value in locals_dict.items():
        if previous_locals.get(variable_name) != variable_value:
            insert_event(
                conn,
                frame.f_lineno,
                variable_name,
                repr(variable_value),
            )

    previous_locals = locals_dict.copy()

    return trace_callback


# Read target file
with open(TARGET_FILE, "r", encoding="utf-8") as f:
    source = f.read()

# Compile target file
code = compile(source, TARGET_FILE, "exec")

# Namespace for execution
exec_globals = {
    "__name__": "__main__",
    "__file__": TARGET_FILE,
}

# Start tracing
sys.settrace(trace_callback)

try:
    exec(code, exec_globals)
finally:
    sys.settrace(None)
    conn.close()