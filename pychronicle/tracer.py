import sys
import os

TARGET_FILE = os.path.abspath("test/fixtures/test_target.py") 


def trace_callback(frame, event, arg):
    if os.path.abspath(frame.f_code.co_filename) != TARGET_FILE:
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

    return trace_callback


# Read target file
with open(TARGET_FILE, "r", encoding="utf-8") as f:
    source = f.read()

# Compile target file
code = compile(source, TARGET_FILE, "exec")

# Separate namespace
exec_globals = {
    "__name__": "__main__",
    "__file__": TARGET_FILE,
}

# Start tracing
sys.settrace(trace_callback)

# Execute
exec(code, exec_globals)

# Stop tracing
sys.settrace(None)