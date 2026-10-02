from __future__ import annotations

from ..menu_context import MenuContext


def is_enabled(context: MenuContext) -> bool:
    return True


def run(context: MenuContext) -> None:
    if context.editor_view is not None:
        buffer = context.editor_view.get_buffer()
        bounds = buffer.get_bounds()
        start = bounds.start if hasattr(bounds, "start") else bounds[0]
        end = bounds.end if hasattr(bounds, "end") else bounds[1]
        buffer.select_range(start, end)
    elif context.terminal_widget is not None:
        context.terminal_widget.select_all()
    elif context.tree is not None:
        context.tree.get_selection().select_all()
    else:
        context.widget.grab_focus()