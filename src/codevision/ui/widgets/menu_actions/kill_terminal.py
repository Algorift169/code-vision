from __future__ import annotations

from ..menu_context import MenuContext


def is_enabled(context: MenuContext) -> bool:
    return context.kind == "terminal" and context.close_terminal_tab is not None


def run(context: MenuContext) -> None:
    if context.close_terminal_tab is not None:
        context.close_terminal_tab()