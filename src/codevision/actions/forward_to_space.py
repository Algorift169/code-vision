from __future__ import annotations

from typing import TYPE_CHECKING

from .helpers import (
    analysis_panel_for,
    graph_node_for_context,
    space_view_for,
    text_from_widget,
)

if TYPE_CHECKING:
    from ..ui.widgets.menu_context import MenuContext


def is_enabled(context: MenuContext) -> bool:
    panel = analysis_panel_for(context)
    return (
        context.kind == "analysis-panel"
        and panel is not None
        and space_view_for(context) is not None
        and (
            graph_node_for_context(context) is not None
            or text_from_widget(context.widget) is not None
            or panel.source_text is not None
        )
    )


def run(context: MenuContext) -> None:
    panel = analysis_panel_for(context)
    space = space_view_for(context)
    if panel is None or space is None:
        return
    graph_node = graph_node_for_context(context)
    panel.select_section("Space")
    if graph_node is not None:
        space.add_graph_node(graph_node)
        return
    text = text_from_widget(context.widget) or panel.source_text
    if text:
        space.add_text_box(text)
