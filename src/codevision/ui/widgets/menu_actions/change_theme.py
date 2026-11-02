from __future__ import annotations

from ..menu_context import MenuContext


def is_enabled(context: MenuContext) -> bool:
    return context.open_theme_menu is not None


def run(context: MenuContext) -> None:
    if context.open_theme_menu is not None:
        context.open_theme_menu(context.widget)
