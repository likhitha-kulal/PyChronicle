"""
scratch/week3_preview.py

Week 3 preview — NOT production code yet.
P1 writes and tests these visitor methods here before adding them
to hook_injector.py in Week 3.

This file answers the question: "How do I handle each missing
assignment type?" so Week 3 Day 1 is copying, not figuring out.
"""

import ast


HOOK = "__pychronicle_hook__"


def _copy_loc(new_node: ast.AST, anchor: ast.AST) -> ast.AST:
    """Stamp every child of new_node with anchor's location."""
    for child in ast.walk(new_node):
        ast.copy_location(child, anchor)
    return new_node


def _make_hook_call(var_name: str, anchor: ast.AST) -> ast.Expr:
    """Build: __pychronicle_hook__('var_name', var_name, lineno)"""
    expr = ast.Expr(
        value=ast.Call(
            func=ast.Name(id=HOOK, ctx=ast.Load()),
            args=[
                ast.Constant(value=var_name),
                ast.Name(id=var_name, ctx=ast.Load()),
                ast.Constant(value=anchor.lineno),
            ],
            keywords=[],
        )
    )
    return _copy_loc(expr, anchor)


class Week3Injector(ast.NodeTransformer):
    """
    Preview of Week 3's expanded HookInjector.
    Adds three new visitor methods on top of the existing visit_Assign.
    """

    # ── Already exists in hook_injector.py ───────────────────────────
    def visit_Assign(self, node: ast.Assign) -> list[ast.stmt]:
        self.generic_visit(node)
        calls = []
        for target in node.targets:
            if isinstance(target, ast.Name):
                calls.append(_make_hook_call(target.id, node))
            elif isinstance(target, (ast.Tuple, ast.List)):
                for elt in target.elts:
                    if isinstance(elt, ast.Name):
                        calls.append(_make_hook_call(elt.id, node))
        return [node, *calls]

    # ── NEW Week 3 ────────────────────────────────────────────────────
    def visit_AugAssign(self, node: ast.AugAssign) -> list[ast.stmt]:
        """
        Handles: x += 1, x -= 2, x *= 3 etc.

        Difference from visit_Assign:
          - node.target is singular (not a list)
          - Only ast.Name targets make sense here
            (you can't do [a, b] += something)
        """
        self.generic_visit(node)
        if isinstance(node.target, ast.Name):
            return [node, _make_hook_call(node.target.id, node)]
        return [node]

    def visit_AnnAssign(self, node: ast.AnnAssign) -> list[ast.stmt]:
        """
        Handles: x: int = 5

        Difference from visit_Assign:
          - node.target is singular
          - node.value can be None (declaration only: x: int)
            In that case nothing is assigned so no hook needed
        """
        self.generic_visit(node)
        if node.value is not None and isinstance(node.target, ast.Name):
            return [node, _make_hook_call(node.target.id, node)]
        return [node]

    def visit_For(self, node: ast.For) -> list[ast.stmt]:
        """
        Handles: for i in range(n):

        The loop variable `i` is bound by the For node itself —
        NOT by any Assign node inside the loop body. That's why
        it's currently invisible to the injector.

        Strategy: inject a hook call as the FIRST statement inside
        the loop body, so it fires at the start of every iteration
        after `i` has been bound.
        """
        self.generic_visit(node)
        if isinstance(node.target, ast.Name):
            hook = _make_hook_call(node.target.id, node)
            # Prepend to body — fires first thing each iteration
            node.body = [hook, *node.body]
        return [node]


# ── Tests — run this file directly to verify all three work ──────────

def _run(source: str) -> list[tuple]:
    """Helper: inject and exec source, return captured log."""
    log = []
    tree = ast.parse(source)
    new_tree = Week3Injector().visit(tree)
    ast.fix_missing_locations(new_tree)
    rewritten = ast.unparse(new_tree)
    exec(rewritten, {HOOK: lambda n, v, l: log.append((n, v, l))})
    return log


if __name__ == "__main__":
    print("Testing AugAssign (x += 1)...")
    log = _run("x = 0\nfor i in range(3):\n    x += i\n")
    x_entries = [(n, v) for n, v, l in log if n == "x"]
    assert x_entries == [("x", 0), ("x", 0), ("x", 1), ("x", 3)], \
        f"AugAssign FAIL: {x_entries}"
    print(f"  PASSED — x captured {len(x_entries)} times: {x_entries}")

    print("\nTesting AnnAssign (x: int = 5)...")
    log = _run("x: int = 5\ny: str\n")  # y has no value — no hook
    names = {n for n, v, l in log}
    assert "x" in names, "AnnAssign FAIL: x not captured"
    assert "y" not in names, "AnnAssign FAIL: y should not be captured (no value)"
    print(f"  PASSED — x captured, y (no value) skipped")

    print("\nTesting For loop variable (for i in range(3))...")
    log = _run("for i in range(3):\n    x = i * 2\n")
    i_entries = [(n, v) for n, v, l in log if n == "i"]
    assert len(i_entries) == 3, \
        f"For loop FAIL: i captured {len(i_entries)} times, expected 3"
    assert [v for n, v in i_entries] == [0, 1, 2], \
        f"For loop FAIL: wrong values {i_entries}"
    print(f"  PASSED — i captured {len(i_entries)} times: {i_entries}")

    print("\nAll Week 3 preview tests PASSED ✓")
    print("Ready to merge into hook_injector.py on Week 3 Day 1")