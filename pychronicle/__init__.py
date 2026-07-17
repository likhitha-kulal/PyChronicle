"""
pychronicle — AST-powered time-travel debugger.

This package's __init__.py exposes the public API surface that other
team members (P2 tracer, P3 storage, P4 TUI) import from. Keep this
file thin: it should only re-export, never contain logic.
"""

from pychronicle.ast_parser import find_assignments
from pychronicle.hook_injector import inject_hooks, HookInjector
from pychronicle.db import (
    init_db,
    insert_event,
    insert_events_batch,
    query_by_line,
    get_total_steps,
    get_event_at_step,
    get_all_variables_state_at_step,
)

__all__ = [
    "find_assignments",
    "inject_hooks",
    "HookInjector",
    "init_db",
    "insert_event",
    "insert_events_batch",
    "query_by_line",
    "get_total_steps",
    "get_event_at_step",
    "get_all_variables_state_at_step",
]

__version__ = "0.1.0"
