from __future__ import annotations

from typing import TYPE_CHECKING

from .helpers import analysis_view_for, select_all_available, text_view_for

if TYPE_CHECKING:
    from ..ui.widgets.menu_context import MenuContext


def is_enabled(context: MenuContext) -> bool:
    return context.kind == "analysis-panel" and select_all_available(context)


def run(context: MenuContext) -> None:
    text_view = text_view_for(context.widget)
    if text_view is not None:
        buffer = text_view.get_buffer()
        buffer.select_range(buffer.get_start_iter(), buffer.get_end_iter())
        return
    view = analysis_view_for(context)
    select_all = getattr(view, "select_all_nodes", None)
    if callable(select_all):
        select_all()
