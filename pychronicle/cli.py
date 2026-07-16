"""
cli.py — Command-line entrypoint for PyChronicle.
Owner: P1 | Week: 4

Usage:
    pychronicle run myscript.py
    pychronicle run myscript.py --db trace.db
    pychronicle run myscript.py --no-tui

Installed as a script via pyproject.toml:
    [project.scripts]
    pychronicle = "pychronicle.cli:main"
"""

from __future__ import annotations

import sys
import os

try:
    import typer
except ImportError:
    print("Install typer: pip install typer")
    sys.exit(1)

app = typer.Typer(
    name="pychronicle",
    help="AST-powered time-travel debugger — record and replay Python execution.",
    add_completion=False,
)


@app.command()
def run(
    script: str = typer.Argument(..., help="Path to the Python script to trace."),
    db: str = typer.Option("trace.db", "--db", help="SQLite database path."),
    no_tui: bool = typer.Option(False, "--no-tui", help="Skip TUI, just trace."),
) -> None:
    """
    Instrument SCRIPT, run it, record all variable changes to DB,
    then open the time-travel TUI (unless --no-tui is set).
    """
    if not os.path.exists(script):
        typer.echo(f"Error: file not found: {script}", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"[pychronicle] Tracing: {script}")
    typer.echo(f"[pychronicle] Database: {db}")

    # Step 1: run the tracer (P2)
    from pychronicle.tracer import run_traced
    run_traced(script, db_path=db)
    typer.echo(f"[pychronicle] Trace complete. Events written to {db}")

    # Step 2: launch TUI (P4) unless suppressed
    if not no_tui:
        from pychronicle.tui.app import PyChronicleApp
        import sqlite3
        conn = sqlite3.connect(db)
        PyChronicleApp(filepath=script, conn=conn).run()
        conn.close()


def main() -> None:
    app()


if __name__ == "__main__":
    main()
