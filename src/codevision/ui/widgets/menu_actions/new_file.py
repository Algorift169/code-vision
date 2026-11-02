from __future__ import annotations

from ..menu_context import MenuContext


def is_enabled(context: MenuContext) -> bool:
    return context.open_action_menu is not None


def run(context: MenuContext) -> None:
    if context.open_action_menu is not None:
        context.open_action_menu(
            "new-file", context, context.action_anchor or context.widget
        )