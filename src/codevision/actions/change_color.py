from __future__ import annotations

from typing import TYPE_CHECKING

from .helpers import analysis_panel_for, space_item_for, space_view_for
from space.textbox import TextBox

if TYPE_CHECKING:
    from ..ui.widgets.menu_context import MenuContext


def is_enabled(context: MenuContext) -> bool:
    panel = analysis_panel_for(context)
    return (
        context.kind == "analysis-panel"
        and panel is not None
        and panel.current_section == "Space"
        and isinstance(space_item_for(context), TextBox)
    )


def run(context: MenuContext) -> None:
    text_box = space_item_for(context)
    space = space_view_for(context)
    if isinstance(text_box, TextBox) and space is not None:
        space.open_color_palette_for(text_box)
