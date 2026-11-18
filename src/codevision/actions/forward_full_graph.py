from __future__ import annotations

from typing import TYPE_CHECKING

from .helpers import analysis_panel_for, graph_snapshot_for, space_view_for

if TYPE_CHECKING:
    from ..ui.widgets.menu_context import MenuContext


def is_enabled(context: MenuContext) -> bool:
    graph = graph_snapshot_for(context)
    return (
        context.kind == "analysis-panel"
        and analysis_panel_for(context) is not None
        and space_view_for(context) is not None
        and graph is not None
        and bool(graph.nodes)
    )


def run(context: MenuContext) -> None:
    panel = analysis_panel_for(context)
    space = space_view_for(context)
    graph = graph_snapshot_for(context)
    if panel is None or space is None or graph is None:
        return
    panel.select_section("Space")
    space.add_graph(graph)
