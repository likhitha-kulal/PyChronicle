"""
hook_injector.py — AST rewriter that injects state-capture hooks.
Owner: P1 (AST Engineer)
Weeks: 2-3

ROLE CLARIFICATION (after company requirements review, Week 3):
    This module is a PRECISION SUPPLEMENT to sys.settrace (P2's engine).
    sys.settrace is the primary capture mechanism — it fires on every line.
    inject_hooks() adds exact assignment-level precision markers that
    sys.settrace alone cannot provide (exact moment of assignment).

    P2's tracer.py uses sys.settrace as primary.
    P2 may optionally use inject_hooks() for enhanced precision in Week 3.

Where ast_parser.py only READS the tree, this module REWRITES it.
After each assignment it inserts a hook call:

    x = 5               ->  x = 5
                            __pychronicle_hook__('x', x, 1)

    x += 1              ->  x += 1                  (Week 3)
                            __pychronicle_hook__('x', x, 2)

    x: int = 5          ->  x: int = 5              (Week 3)
                            __pychronicle_hook__('x', x, 3)

    for i in range(n):  ->  for i in range(n):      (Week 3)
                                __pychronicle_hook__('i', i, 4)
                                ...

Public API:
    inject_hooks(source_code, hook_name) -> str
    HookInjector  (NodeTransformer, exposed for testing/extension)
"""

from __future__ import annotations

import ast


class HookInjector(ast.NodeTransformer):
    """
    Walks the AST and inserts hook calls after every assignment.

    Handles 4 node types (3 added in Week 3):
        ast.Assign    — x = 5, a, b = 1, 2, c = d = 10   (Week 2)
        ast.AugAssign — x += 1, x -= 2, x *= 3            (Week 3)
        ast.AnnAssign — x: int = 5                         (Week 3)
        ast.For       — for i in range(n):                  (Week 3)

    Usage:
        tree = ast.parse(source)
        new_tree = HookInjector().visit(tree)
        ast.fix_missing_locations(new_tree)
        rewritten = ast.unparse(new_tree)
    """

    def __init__(self, hook_name: str = "__pychronicle_hook__") -> None:
        super().__init__()
        self.hook_name = hook_name

    # ── shared helper ─────────────────────────────────────────────────

    def _make_call(self, var_name: str, anchor: ast.AST) -> ast.Expr:
        """
        Build: __pychronicle_hook__('var_name', var_name, lineno)

        anchor is the original AST node (Assign/AugAssign/AnnAssign/For).
        Every child of the new Expr copies its location from anchor so
        compile() gets valid lineno/col_offset/end_lineno/end_col_offset
        on all nodes. Without this, compile() raises:
            ValueError: AST node line range (N, 0) is not valid
        """
        call = ast.Expr(
            value=ast.Call(
                func=ast.Name(id=self.hook_name, ctx=ast.Load()),
                args=[
                    ast.Constant(value=var_name),
                    ast.Name(id=var_name, ctx=ast.Load()),
                    ast.Constant(value=anchor.lineno),
                ],
                keywords=[],
            )
        )
        # Stamp every node with anchor's real location data
        for child in ast.walk(call):
            ast.copy_location(child, anchor)
        return call

    def _calls_for_target(
        self,
        target: ast.expr,
        anchor: ast.AST,
    ) -> list[ast.Expr]:
        """
        Recursively build hook calls for a (possibly nested) target.

        Handles:
            ast.Name              -> x = 5       captures x
            ast.Tuple / ast.List  -> a, b = 1, 2  captures a and b

        Intentionally skips:
            ast.Subscript  -> items[0] = 1  (not a variable name)
            ast.Attribute  -> obj.x = 1     (not a local variable)
        """
        calls: list[ast.Expr] = []
        if isinstance(target, ast.Name):
            calls.append(self._make_call(target.id, anchor))
        elif isinstance(target, (ast.Tuple, ast.List)):
            for elt in target.elts:
                calls.extend(self._calls_for_target(elt, anchor))
        return calls

    # ── Week 2: regular assignments ───────────────────────────────────

    def visit_Assign(self, node: ast.Assign) -> list[ast.stmt]:
        """
        Handles: x = 5  |  a, b = 1, 2  |  c = d = 10

        node.targets is a LIST because chained assignment (c = d = 10)
        has two targets. We build a hook call for each target.
        """
        self.generic_visit(node)

        hook_calls: list[ast.stmt] = []
        for target in node.targets:
            hook_calls.extend(self._calls_for_target(target, node))

        return [node, *hook_calls]

    # ── Week 3 Addition 1: augmented assignments ──────────────────────

    def visit_AugAssign(self, node: ast.AugAssign) -> list[ast.stmt]:
        """
        Handles: x += 1, x -= 2, x *= 3, x //= 2 etc.

        Key differences from visit_Assign:
            node.target  is SINGULAR  (no 's' — there is only ever one)
            node.op      is the operator (Add, Sub, Mult ...)
            node.value   is the right-hand side

        Cannot have tuple targets — `a, b += 1, 2` is a SyntaxError
        in Python, so we only ever need to check for ast.Name here.

        Why it was missing before Week 3:
            ast.AugAssign is a completely different node type from
            ast.Assign — visit_Assign is never called for x += 1.
            The injector silently skipped it because there was no
            visit_AugAssign method to catch it.
        """
        self.generic_visit(node)

        if isinstance(node.target, ast.Name):
            return [node, self._make_call(node.target.id, node)]

        # Non-Name targets (e.g. obj.attr += 1) — skip hook, return as-is
        return [node]

    # ── Week 3 Addition 2: annotated assignments ──────────────────────

    def visit_AnnAssign(self, node: ast.AnnAssign) -> list[ast.stmt]:
        """
        Handles: x: int = 5

        Key differences from visit_Assign:
            node.target      is SINGULAR (always one variable)
            node.annotation  is the type hint (int, str, list, etc.)
            node.value       can be NONE for bare declarations (x: int)

        We must check node.value is not None before injecting a hook.
        A bare `x: int` declares a type but assigns nothing — there is
        no value to capture, so no hook call should be inserted.

        Why it was missing before Week 3:
            Same reason as AugAssign — completely separate node type.
        """
        self.generic_visit(node)

        if node.value is not None and isinstance(node.target, ast.Name):
            return [node, self._make_call(node.target.id, node)]

        # Bare declaration (x: int with no value) — nothing assigned
        return [node]

    # ── Week 3 Addition 3: for-loop variables ─────────────────────────

    def visit_For(self, node: ast.For) -> list[ast.stmt]:
        """
        Handles: for i in range(n):

        Why the loop variable was invisible before Week 3:
            `for i in range(n):` does NOT create an ast.Assign node.
            The binding of `i` is performed by the For node itself via
            its .target field. visit_Assign never fires for it, which
            is why `i` never appeared in hook captures before.

        Strategy — prepend the hook as the FIRST statement in the body:
            for i in range(n):
                __pychronicle_hook__('i', i, <lineno>)  # inserted first
                ... rest of body ...

        This fires at the START of every iteration, immediately after
        Python has bound the new value of `i` for that iteration.
        Appending to the end would capture the PREVIOUS iteration's
        value because the next iteration's binding hasn't happened yet.

        Only handles simple `ast.Name` loop targets. Tuple unpacking
        in for-loops (for a, b in pairs:) is a future enhancement.
        """
        self.generic_visit(node)

        if isinstance(node.target, ast.Name):
            hook = self._make_call(node.target.id, node)
            # Prepend — fires right at the start of each iteration
            node.body = [hook, *node.body]

        return [node]


def inject_hooks(
    source_code: str,
    hook_name: str = "__pychronicle_hook__",
) -> str:
    """
    Inject hook calls into source_code and return rewritten source.

    Takes raw Python source string, rewrites assignments to add hook
    calls, returns the rewritten source ready to compile() and exec().

    From Week 3 onward, handles: =, +=, : int =, for loops.

    Args:
        source_code: raw Python source string.
        hook_name:   name of the hook function — must be available in
                     exec() globals when running the rewritten code.

    Returns:
        Rewritten Python source as a string.
    """
    tree = ast.parse(source_code)
    new_tree = HookInjector(hook_name=hook_name).visit(tree)
    ast.fix_missing_locations(new_tree)
    return ast.unparse(new_tree)


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python hook_injector.py <path_to_script.py>")
        sys.exit(1)

    with open(sys.argv[1], "r", encoding="utf-8") as f:
        original = f.read()

    print(inject_hooks(original))