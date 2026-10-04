from __future__ import annotations

from ..menu_context import MenuContext


def is_enabled(context: MenuContext) -> bool:
    return context.open_kong_browser is not None


def run(context: MenuContext) -> None:
    if context.open_kong_browser is None:
        return
    target = context.selected_text if context.selected_text else None
    context.open_kong_browser(target)
