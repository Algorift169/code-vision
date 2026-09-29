from __future__ import annotations

from ..menu_context import MenuContext


def is_enabled(context: MenuContext) -> bool:
    return True


def run(context: MenuContext) -> None:
    if context.select_target is not None:
        context.select_target()
        return
    if context.terminal_widget is not None:
        context.terminal_widget.grab_focus()
        return
    if context.editor_view is None:
        context.widget.grab_focus()
        return

    buffer = context.editor_view.get_buffer()
    cursor = buffer.get_iter_at_mark(buffer.get_insert())
    start = cursor.copy()
    end = cursor.copy()
    if not start.starts_word():
        start.backward_word_start()
    end.forward_word_end()
    if start.compare(end) < 0:
        buffer.select_range(start, end)