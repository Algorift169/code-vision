from __future__ import annotations

from typing import TYPE_CHECKING

from .helpers import analysis_panel_for

if TYPE_CHECKING:
    from ..ui.widgets.menu_context import MenuContext


def is_enabled(context: MenuContext) -> bool:
    return context.kind == "analysis-panel" and analysis_panel_for(context) is not None


def run(context: MenuContext) -> None:
    panel = analysis_panel_for(context)
    if panel is not None:
        panel.select_section("Complexity")
