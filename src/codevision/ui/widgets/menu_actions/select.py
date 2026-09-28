from __future__ import annotations

from ..menu_context import MenuContext


def is_enabled(context: MenuContext) -> bool:
    return context.editor_view is not None or (
        context.path is not None and context.select_target is not None
    )


def run(context: MenuContext) -> None:
    if context.select_target is not None:
        context.select_target()
        return
    if context.editor_view is None:
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