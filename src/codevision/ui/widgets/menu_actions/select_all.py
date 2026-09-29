from __future__ import annotations

from ..menu_context import MenuContext


def is_enabled(context: MenuContext) -> bool:
    return True


def run(context: MenuContext) -> None:
    if context.editor_view is not None:
        buffer = context.editor_view.get_buffer()
        buffer.select_range(*buffer.get_bounds())
    elif context.terminal_widget is not None:
        context.terminal_widget.select_all()
    elif context.tree is not None:
        context.tree.get_selection().select_all()
    else:
        context.widget.grab_focus()