from __future__ import annotations

from typing import TYPE_CHECKING

from .helpers import analysis_panel_for, space_view_for

if TYPE_CHECKING:
    from ..ui.widgets.menu_context import MenuContext


def is_enabled(context: MenuContext) -> bool:
    panel = analysis_panel_for(context)
    return (
        context.kind == "analysis-panel"
        and panel is not None
        and panel.current_section == "Space"
    )


def run(context: MenuContext) -> None:
    if is_enabled(context):
        space = space_view_for(context)
        if space is not None:
            space.clear_board()
