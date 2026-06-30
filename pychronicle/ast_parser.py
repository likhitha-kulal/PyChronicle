"""
ast_parser.py — finds variable assignments in a Python file.

Owner: P1 (AST Engineer)
Week: 1

This module is READ-ONLY analysis: it parses a target script's Abstract
Syntax Tree and reports every line where a simple variable assignment
occurs. It does not modify the script in any way — that is the job of
hook_injector.py (Week 2-3).

Public API:
    find_assignments(filepath) -> list[tuple[int, str]]
"""

from __future__ import annotations

import ast


def find_assignments(filepath: str) -> list[tuple[int, str]]:
    """
    Parse a Python file and return every simple variable assignment.

    Args:
        filepath: path to a .py file on disk.

    Returns:
        A list of (line_number, variable_name) tuples, one entry per
        simple name target. Order follows the order nodes are visited
        by ast.walk (roughly top-to-bottom, but not strictly guaranteed
        for deeply nested structures).

    Notes:
        - Only ast.Name targets are captured (e.g. `x = 5`).
        - Tuple unpacking is captured per-name (e.g. `a, b = 1, 2`
          yields two entries: (line, 'a') and (line, 'b')).
        - Chained assignment is captured per-target (e.g. `c = d = 10`
          yields two entries: (line, 'c') and (line, 'd')).
        - Subscript assignment (`items[0] = 99`) and attribute
          assignment (`obj.x = 99`) are intentionally skipped, since
          their "target" isn't a single named variable.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        source = f.read()

    tree = ast.parse(source, filename=filepath)
    results: list[tuple[int, str]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                _collect_names(target, node.lineno, results)

    return results


def _collect_names(
    target: ast.expr, lineno: int, results: list[tuple[int, str]]
) -> None:
    """
    Recursively collect simple names from an assignment target.

    Handles plain names (`x`) and tuple/list unpacking
    (`a, b = ...` or `[a, b] = ...`). Skips subscripts and attributes.
    """
    if isinstance(target, ast.Name):
        results.append((lineno, target.id))
    elif isinstance(target, (ast.Tuple, ast.List)):
        for elt in target.elts:
            _collect_names(elt, lineno, results)
    # ast.Subscript, ast.Attribute, ast.Starred -> intentionally skipped


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python ast_parser.py <path_to_script.py>")
        sys.exit(1)

    for line, name in find_assignments(sys.argv[1]):
        print(f"Line {line}: {name}")