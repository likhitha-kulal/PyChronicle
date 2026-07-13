
"""
hook_injector.py — rewrites a target script's AST to inject state-capturing
hooks after every assignment, without modifying the original source file.
 
Owner: P1 (AST Engineer)
Week: 2-3 (Day 6 preview, built out fully in Week 2-3)
 
Where ast_parser.py only *reads* the tree (ast.walk), this module
*rewrites* it (ast.NodeTransformer). After each assignment statement,
it inserts a call to a hook function:
 
    x = 5
    # becomes:
    x = 5
    __pychronicle_hook__('x', x, 5)   # (var_name, value, lineno)
 
The hook function itself is supplied by P2 (the tracer) at run time —
this module only handles the AST rewriting, not what the hook does
with the captured data. That keeps a clean boundary between P1 and P2.
 
Public API:
    inject_hooks(source_code, hook_name="__pychronicle_hook__") -> str
    HookInjector (the NodeTransformer class, exposed for testing/extension)
"""
 
from __future__ import annotations
 
import ast
 
 
class HookInjector(ast.NodeTransformer):
    """
    Walks the AST and, for every simple-name assignment, inserts a
    call to `hook_name` immediately after it.
 
    Usage:
        tree = ast.parse(source)
        injector = HookInjector(hook_name="__pychronicle_hook__")
        new_tree = injector.visit(tree)
        ast.fix_missing_locations(new_tree)
        new_source = ast.unparse(new_tree)
    """
 
    def __init__(self, hook_name: str = "__pychronicle_hook__") -> None:
        super().__init__()
        self.hook_name = hook_name
 
    # ------------------------------------------------------------------ #
    # CHANGED (Day 3): pass full `node` as `anchor` instead of just       #
    # `node.lineno` so _make_call() has a real AST node to copy           #
    # location from. Before this fix, _make_call() received only an int   #
    # and had no real node to copy_location from, causing ValueError       #
    # from compile() about invalid line ranges.                            #
    # ------------------------------------------------------------------ #
    def visit_Assign(self, node: ast.Assign) -> list[ast.stmt]:
        # Always visit children first in case of nested assignments
        self.generic_visit(node)
 
        hook_calls: list[ast.stmt] = []
        for target in node.targets:
            # ✅ Pass full `node` (the Assign) not just `node.lineno`
            hook_calls.extend(self._build_hook_calls(target, node))
 
        # Return the original assignment followed by hook call(s)
        return [node, *hook_calls]
 
    # ------------------------------------------------------------------ #
    # CHANGED (Day 3): parameter renamed from `lineno: int` to            #
    # `anchor: ast.Assign` — receives the full original Assign node       #
    # so it can be forwarded to _make_call() for location copying.        #
    # ------------------------------------------------------------------ #
    def _build_hook_calls(
        self,
        target: ast.expr,
        anchor: ast.Assign,          # ✅ was `lineno: int`
    ) -> list[ast.stmt]:
        """Build hook-call statements for a (possibly nested) target."""
        calls: list[ast.stmt] = []
 
        if isinstance(target, ast.Name):
            # ✅ Forward anchor, not just anchor.lineno
            calls.append(self._make_call(target.id, anchor))
        elif isinstance(target, (ast.Tuple, ast.List)):
            for elt in target.elts:
                # ✅ Recurse with anchor, not lineno
                calls.extend(self._build_hook_calls(elt, anchor))
        # Subscript / Attribute targets are intentionally skipped,
        # consistent with ast_parser.py's behaviour.
 
        return calls
 
    # ------------------------------------------------------------------ #
    # CHANGED : parameter renamed from `lineno: int` to            #
    # `anchor: ast.Assign`. The key fix is the loop at the bottom:        #
    #                                                                      #
    #   OLD (broken):                                                      #
    #       ast.copy_location(call, call.value)  <- self-referential,     #
    #       call.value has no location yet either, so both nodes end up   #
    #       with lineno=0 / end_lineno=0 which compile() rejects with     #
    #       "AST node line range (N, 0) is not valid".                    #
    #                                                                      #
    #   NEW (fixed):                                                       #
    #       for child in ast.walk(call):                                  #
    #           ast.copy_location(child, anchor)                          #
    #       anchor is the real ast.Assign node from the parsed source,    #
    #       it already has lineno, col_offset, end_lineno, end_col_offset #
    #       all set correctly by ast.parse(). Stamping every node in the  #
    #       new Expr with these values gives compile() consistent,        #
    #       valid location data throughout the injected subtree.          #
    # ------------------------------------------------------------------ #
    def _make_call(
        self,
        var_name: str,
        anchor: ast.Assign,          # ✅ was `lineno: int`
    ) -> ast.Expr:
        """
        Build the AST node for:
 
            __pychronicle_hook__('var_name', var_name, lineno)
 
        All nodes in the returned Expr have their location copied from
        `anchor` (the original Assign node from the parsed source).
        This is required because compile() validates that every node in
        the tree has a complete, internally consistent location — new
        nodes created by a NodeTransformer do not have this by default.
        """
        call = ast.Expr(
            value=ast.Call(
                func=ast.Name(id=self.hook_name, ctx=ast.Load()),
                args=[
                    ast.Constant(value=var_name),
                    ast.Name(id=var_name, ctx=ast.Load()),
                    # ✅ anchor.lineno — same integer value as before,
                    # but now derived from the real node
                    ast.Constant(value=anchor.lineno),
                ],
                keywords=[],
            )
        )
 
        # ✅ THE CORE FIX:
        # Walk every node inside our new Expr and stamp it with the
        # location from anchor. ast.copy_location sets:
        #   .lineno, .col_offset, .end_lineno, .end_col_offset
        # all of which compile() requires to be present and consistent.
        for child in ast.walk(call):
            ast.copy_location(child, anchor)
 
        return call
 
 
def inject_hooks(
    source_code: str,
    hook_name: str = "__pychronicle_hook__",
) -> str:
    """
    Take raw Python source, inject hook calls after every assignment,
    and return the rewritten source as a string.
 
    Args:
        source_code: the original script's source, as a string.
        hook_name:   the name of the hook function that will be called.
                     The caller (P2's tracer) is responsible for making
                     a function with this name available in the exec()
                     globals when running the rewritten code.
 
    Returns:
        Rewritten Python source code as a string, ready to be
        compiled and exec'd.
    """
    tree = ast.parse(source_code)
    injector = HookInjector(hook_name=hook_name)
    new_tree = injector.visit(tree)
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