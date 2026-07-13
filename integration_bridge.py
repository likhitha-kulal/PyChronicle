"""
integration_bridge.py

Written by P1 on Week 2 Day 5.
Purpose: prove to P2 that inject_hooks() works correctly as a drop-in
source for exec(). P2 copies the run_with_hook() pattern directly into
tracer.py — the only thing P2 changes is replacing demo_hook with a
function that writes to P3's database instead of printing.

Run:
    python integration_bridge.py test/fixtures/test_target.py
"""

import sys
from pychronicle.hook_injector import inject_hooks


def run_with_hook(filepath: str, hook_fn) -> None:
    """
    This is the exact pattern P2's tracer.py will use.

    Step 1: read the source file
    Step 2: inject_hooks() rewrites it — inserts hook calls after
            every assignment
    Step 3: compile() turns the rewritten string into bytecode
    Step 4: exec() runs it with hook_fn available in globals so
            the injected __pychronicle_hook__() calls can resolve

    P2's run_traced() wraps this with:
        conn = init_db(db_path)       <- before
        hook_fn = _hook_fn(conn)      <- replace demo_hook with this
        conn.commit(); conn.close()   <- after
    """
    with open(filepath, "r", encoding="utf-8") as f:
        source = f.read()

    rewritten = inject_hooks(source)
    code = compile(rewritten, filepath, "exec")

    # __pychronicle_hook__ must be in exec globals —
    # this is how the injected calls find the function
    exec_globals = {
        "__pychronicle_hook__": hook_fn,
        "__name__": "__pychronicle_target__",
    }

    exec(code, exec_globals)


# ── Demo hook: print-based, no DB needed ─────────────────────────────
captured = []

def demo_hook(var_name: str, value, lineno: int) -> None:
    """
    P2 replaces this with a function that calls P3's insert_event().
    The signature must stay exactly: (var_name: str, value, lineno: int)
    """
    captured.append((var_name, value, lineno))
    print(f"  [line {lineno:3d}] {var_name} = {value!r}")


# ── Self-verification after run ───────────────────────────────────────
def verify(filepath: str) -> None:
    """
    After running, check the captured log to confirm:
    1. Something was captured at all
    2. All expected variables appear
    3. Loop variables appear multiple times (not just once)
    4. Line numbers are never 0
    """
    print("\n── Verification ──────────────────────────────")

    # Check 1: something was captured
    assert len(captured) > 0, "FAIL: nothing captured — hook not firing"
    print(f"✓ Total captures : {len(captured)}")

    # Check 2: expected variables appear
    names = {n for n, v, l in captured}
    for expected in ["total", "squared", "x", "y", "a", "b", "items"]:
        assert expected in names, f"FAIL: missing variable '{expected}'"
    print(f"✓ Variables found : {sorted(names)}")

    # Check 3: loop variable 'total' appears more than once
    total_count = sum(1 for n, v, l in captured if n == "total")
    assert total_count > 1, \
        f"FAIL: 'total' captured only {total_count} time(s) — loop not tracing"
    print(f"✓ Loop trace      : 'total' captured {total_count} times")

    # Check 4: no zero line numbers
    zero_lines = [(n, v, l) for n, v, l in captured if l == 0]
    assert not zero_lines, f"FAIL: line number = 0 found in {zero_lines}"
    print(f"✓ Line numbers    : all non-zero")

    print("\nIntegration Bridge: PASSED ✓")
    print("P2 can copy run_with_hook() directly into tracer.py.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python integration_bridge.py <script.py>")
        sys.exit(1)

    filepath = sys.argv[1]
    print(f"Tracing: {filepath}\n")

    run_with_hook(filepath, demo_hook)
    verify(filepath)