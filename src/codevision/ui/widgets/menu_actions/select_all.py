from __future__ import annotations

from ..menu_context import MenuContext


def is_enabled(context: MenuContext) -> bool:
    return context.editor_view is not None or context.tree is not None


def run(context: MenuContext) -> None:
    if context.editor_view is not None:
        buffer = context.editor_view.get_buffer()
        buffer.select_range(*buffer.get_bounds())
    elif context.tree is not None:
        context.tree.get_selection().select_all()