import subprocess
import sys


from pychronicle.ast_parser import find_assignments
from pychronicle.hook_injector import inject_hooks


def test_ast_parser_finds_assignments(tmp_path):
    file = tmp_path / "sample.py"

    file.write_text(
        """
x = 10
y = x + 1
"""
    )

    assignments = find_assignments(str(file))

    assert len(assignments) == 2
    assert assignments[0][1] == "x"
    assert assignments[1][1] == "y"


def test_hook_injector_adds_hook():
    import ast

    source = """
x = 10
y = 20
"""

    tree = ast.parse(source)

    modified_tree = inject_hooks(tree)

    code = compile(
        modified_tree,
        "<test>",
        "exec"
    )

    calls = []

    def __pychronicle_hook__(*args, **kwargs):
        calls.append(args)

    namespace = {
        "__pychronicle_hook__": __pychronicle_hook__
    }

    exec(code, namespace)

    assert namespace["x"] == 10
    assert namespace["y"] == 20
    assert len(calls) > 0


def test_tracer_runs():
    result = subprocess.run(
        [
            sys.executable,
            "pychronicle/tracer.py",
            "test/fixtures/test_target.py",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Event: line" in result.stdout
    assert "total" in result.stdout