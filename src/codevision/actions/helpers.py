from __future__ import annotations

from typing import TYPE_CHECKING

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from space.graph_data import (
    GraphEdgeData,
    GraphNodeData,
    GraphSnapshot,
    GraphTextLine,
)
from space.graph_item import GraphNodeItem
from space.import_item import ImportItem
from space.shape_item import ShapeItem
from space.space_view import SpaceView
from space.textbox import TextBox

from ..ui.analysis_panel import AnalysisPanel

if TYPE_CHECKING:
    from ..ui.widgets.menu_context import MenuContext


def analysis_panel_for(context: MenuContext) -> AnalysisPanel | None:
    panel = context.analysis_panel
    return panel if isinstance(panel, AnalysisPanel) else None


def space_view_for(context: MenuContext) -> SpaceView | None:
    panel = analysis_panel_for(context)
    if panel is None:
        return None
    space = panel._section_placeholders.get("Space")
    return space if isinstance(space, SpaceView) else None


def analysis_view_for(context: MenuContext) -> Gtk.Widget | None:
    panel = analysis_panel_for(context)
    if panel is None:
        return None
    return panel._section_placeholders.get(panel.current_section)


def space_item_for(
    context: MenuContext,
) -> TextBox | ImportItem | GraphNodeItem | ShapeItem | None:
    space = space_view_for(context)
    if space is None:
        return None

    widget: Gtk.Widget | None = context.widget
    while widget is not None:
        if isinstance(widget, (TextBox, ImportItem, GraphNodeItem, ShapeItem)):
            return (
                widget
                if widget
                in (
                    *space.text_boxes,
                    *space.import_items,
                    *space.graph_items,
                    *space.shape_items,
                )
                else None
            )
        widget = widget.get_parent()
    return None


def graph_snapshot_for(context: MenuContext) -> GraphSnapshot | None:
    panel = analysis_panel_for(context)
    if panel is None:
        return None
    section = panel.current_section
    view = panel._section_placeholders.get(section)

    if section == "Flowchart" and view is not None:
        graph = getattr(view, "graph", None)
        if graph is None:
            return None
        text_color = _canvas_text_color(view)
        shapes = {
            "start": "circle",
            "end": "circle",
            "decision": "diamond",
            "loop": "diamond",
            "input": "parallelogram",
            "output": "parallelogram",
            "exception": "hexagon",
            "merge": "small-circle",
            "connector": "small-circle",
        }
        nodes = []
        for node in graph.nodes:
            color = view._NODE_COLORS.get(
                node.kind.value, view._NODE_COLORS["process"]
            )
            selected = (
                view._all_nodes_selected or node.node_id == view._selected_node_id
            )
            labels = node.metadata.get("display_lines") or [node.label]
            first_y = (
                node.height - 14.0 * len(labels)
            ) / 2 + 11.0
            nodes.append(
                GraphNodeData(
                    node.node_id,
                    node.label,
                    node.source_text.strip()
                    or f"{node.kind.value} · Line {node.line or '?'}",
                    node.x,
                    node.y,
                    node.width,
                    node.height,
                    shape=shapes.get(node.kind.value, "rectangle"),
                    fill_color=(*color, 0.20),
                    stroke_color=(
                        (1.0, 0.88, 0.28, 1.0)
                        if selected
                        else (*color, 1.0)
                    ),
                    text_color=text_color,
                    text_lines=tuple(
                        GraphTextLine(
                            text,
                            node.width / 2,
                            first_y + index * 14.0,
                            alignment="center",
                        )
                        for index, text in enumerate(labels)
                    ),
                    stroke_width=3.2 if selected else 2.0,
                )
            )
        nodes = tuple(nodes)
        edges = tuple(
            GraphEdgeData(
                edge.source_id,
                edge.target_id,
                edge.branch_label or "",
            )
            for edge in graph.edges
        )
        return GraphSnapshot(graph.function_name or "Flowchart", nodes, edges)

    if section == "Call Graph" and view is not None:
        graph = getattr(view, "graph", None)
        if graph is None:
            return None
        text_color = _canvas_text_color(view)
        nodes = tuple(
            GraphNodeData(
                node.node_id,
                node.qualified_name or node.name,
                f"Function · Line {node.source_node.location.start_line}"
                if node.source_node is not None
                else "Function",
                node.x,
                node.y,
                node.width,
                node.height,
                fill_color=(
                    (0.97, 0.78, 0.22, 0.38)
                    if view._all_nodes_selected
                    else (0.16, 0.48, 0.42, 0.20)
                ),
                stroke_color=(
                    (0.97, 0.78, 0.22, 1.0)
                    if view._all_nodes_selected
                    else (0.16, 0.48, 0.42, 1.0)
                ),
                text_color=text_color,
                text_lines=(
                    GraphTextLine(node.name, 12, 29),
                    GraphTextLine(
                        f"line {node.source_node.location.start_line}"
                        if node.source_node is not None
                        else "line ?",
                        12,
                        50,
                    ),
                    GraphTextLine(
                        view._connection_summary(graph, node.node_id),
                        12,
                        65,
                        10,
                    ),
                ),
            )
            for node in graph.nodes
        )
        edges = tuple(
            GraphEdgeData(edge.source_id, edge.target_id, edge.label)
            for edge in graph.edges
        )
        return GraphSnapshot("Function Call Graph", nodes, edges)

    if section == "Var Flow" and view is not None:
        graph = getattr(view, "_graph", None)
        if graph is None:
            return None
        colors = {
            "initialization": (0.22, 0.50, 0.78),
            "assignment": (0.38, 0.68, 0.32),
            "merge": (0.82, 0.52, 0.16),
            "usage": (0.72, 0.32, 0.32),
            "read": (0.72, 0.32, 0.32),
            "definition": (0.32, 0.55, 0.75),
            "return": (0.82, 0.30, 0.30),
        }
        nodes = tuple(
            GraphNodeData(
                node.node_id,
                f"{node.kind.title()}: {node.name}",
                node.metadata.get("expression", "")
                or f"{node.scope} · Line {node.metadata.get('source_line', '?')}",
                node.x,
                node.y,
                node.width,
                node.height,
                fill_color=(
                    (0.20, 0.66, 0.89, 1.0)
                    if view._all_nodes_selected
                    or node.node_id == view._selected_node_id
                    else (*colors.get(node.kind, (0.35, 0.52, 0.72)), 1.0)
                ),
                stroke_color=(0.14, 0.15, 0.18, 1.0),
                text_color=(0.95, 0.96, 0.98, 1.0),
                text_lines=(
                    GraphTextLine(node.kind.upper(), 10, 12, 10),
                    GraphTextLine(node.name, 10, 30, 10),
                    GraphTextLine(
                        (node.metadata.get("expression") or "").strip()[:26],
                        10,
                        48,
                        10,
                    ),
                    GraphTextLine(
                        f"Line {node.metadata.get('source_line', '?')}",
                        10,
                        58,
                        10,
                    ),
                ),
                stroke_width=1.5,
            )
            for node in graph.nodes
        )
        edges = tuple(
            GraphEdgeData(edge.source_id, edge.target_id, edge.label)
            for edge in graph.edges
        )
        return GraphSnapshot(f"Variable Flow · {graph.variable_name}", nodes, edges)

    if section == "Dependency" and view is not None:
        foreground = _canvas_text_color(view)
        nodes = []
        for node in view._nodes:
            selected = (
                view._all_nodes_selected or node.selected or node.outgoing_target
            )
            color = (
                (0.97, 0.99, 1.0)
                if node.selected or node.outgoing_target or view._all_nodes_selected
                else view._kind_color(node.kind)
            )
            alpha = 0.12 if node.dimmed else (0.28 if selected else 0.18)
            text_alpha = 0.35 if node.dimmed else 1.0
            nodes.append(
                GraphNodeData(
                    node.node_id,
                    node.label,
                    f"{node.kind} · {node.detail}",
                    node.x,
                    node.y,
                    view.NODE_WIDTH,
                    view.NODE_HEIGHT,
                    fill_color=(*color, alpha),
                    stroke_color=(
                        *color,
                        0.32 if node.dimmed else 0.95,
                    ),
                    text_color=(
                        foreground[0],
                        foreground[1],
                        foreground[2],
                        foreground[3] * text_alpha,
                    ),
                    text_lines=(
                        GraphTextLine(
                            view._fit(node.label, 27),
                            12,
                            27,
                            12 if node.is_group else 13,
                        ),
                        GraphTextLine(
                            view._fit(node.detail, 35),
                            12,
                            51,
                            10,
                        ),
                    ),
                    stroke_width=2.8 if selected else 1.6,
                )
            )
        nodes = tuple(nodes)
        edges = tuple(
            GraphEdgeData(edge.source, edge.target, edge.kind)
            for edge in view._edges
        )
        return GraphSnapshot("Dependency Graph", nodes, edges)

    if section == "AST" and view is not None:
        result = getattr(view, "result", None)
        if result is None:
            return None
        rows_by_depth: dict[int, int] = {}
        depth_by_id: dict[str, int] = {}
        nodes = []
        edges = []
        for node in result.root.walk():
            depth = depth_by_id.get(node.parent_id, -1) + 1
            row = rows_by_depth.get(depth, 0)
            rows_by_depth[depth] = row + 1
            depth_by_id[node.node_id] = depth
            nodes.append(
                GraphNodeData(
                    node.node_id,
                    node.display_name,
                    f"{node.node_type} · Line {node.location.start_line}\n"
                    f"{node.source_text.strip()}",
                    depth * 220.0,
                    row * 96.0,
                    200.0,
                    72.0,
                    text_lines=(
                        GraphTextLine(node.display_name, 12, 27),
                        GraphTextLine(node.node_type, 12, 50, 10),
                    ),
                )
            )
            if node.parent_id is not None:
                edges.append(GraphEdgeData(node.parent_id, node.node_id))
        return GraphSnapshot("Abstract Syntax Tree", tuple(nodes), tuple(edges))

    if section == "Complexity" and view is not None:
        functions = getattr(view, "_filtered_functions", ())
        if not functions:
            return None
        nodes = tuple(
            GraphNodeData(
                f"function-{index}",
                function.name,
                f"Line {function.line} · Cyclomatic {function.cyclomatic} · "
                f"Cognitive {function.cognitive} · {function.risk.title()} risk",
                (index % 3) * 240.0,
                (index // 3) * 100.0,
                216.0,
                78.0,
                text_lines=(
                    GraphTextLine(function.name, 12, 29),
                    GraphTextLine(
                        f"Line {function.line} · Cyclomatic {function.cyclomatic}",
                        12,
                        51,
                        10,
                    ),
                ),
            )
            for index, function in enumerate(functions)
        )
        return GraphSnapshot("Complexity Analysis", nodes, ())

    return None


def _canvas_text_color(view: Gtk.Widget) -> tuple[float, float, float, float]:
    canvas = getattr(view, "canvas", None)
    if not isinstance(canvas, Gtk.Widget):
        return (0.92, 0.94, 0.97, 1.0)
    color = canvas.get_style_context().get_color()
    return (color.red, color.green, color.blue, color.alpha)


def graph_node_for_context(context: MenuContext) -> GraphNodeData | None:
    panel = analysis_panel_for(context)
    view = analysis_view_for(context)
    if panel is None or view is None:
        return None
    snapshot = graph_snapshot_for(context)
    if snapshot is None:
        return None

    widget: Gtk.Widget | None = context.widget
    while widget is not None:
        if isinstance(widget, Gtk.TreeExpander):
            row = widget.get_list_row()
            item = row.get_item() if row is not None else None
            node = getattr(item, "node", None)
            node_id = getattr(node, "node_id", None)
            if node_id is not None:
                match = next(
                    (entry for entry in snapshot.nodes if entry.node_id == node_id),
                    None,
                )
                if match is not None:
                    return match
        if isinstance(widget, Gtk.ListBoxRow):
            function = getattr(widget, "_complexity_item", None)
            functions = getattr(view, "_filtered_functions", ())
            index = next(
                (index for index, item in enumerate(functions) if item is function),
                None,
            )
            if index is not None and index < len(snapshot.nodes):
                return snapshot.nodes[index]
        widget = widget.get_parent()

    if context.analysis_position is None:
        return None
    canvas = getattr(view, "canvas", None)
    if not isinstance(canvas, Gtk.Widget):
        return None
    widget = context.widget
    while widget is not None and widget is not canvas:
        widget = widget.get_parent()
    if widget is None:
        return None

    node_at = getattr(view, "node_at", None)
    if not callable(node_at):
        return None
    node = node_at(*context.analysis_position)
    if node is None:
        return None
    return next(
        (item for item in snapshot.nodes if item.node_id == node.node_id),
        None,
    )


def select_all_available(context: MenuContext) -> bool:
    if text_view_for(context.widget) is not None:
        return True
    view = analysis_view_for(context)
    graph = graph_snapshot_for(context)
    return (
        callable(getattr(view, "select_all_nodes", None))
        and graph is not None
        and bool(graph.nodes)
    )


def text_view_for(widget: Gtk.Widget | None) -> Gtk.TextView | None:
    current = widget
    while current is not None:
        if isinstance(current, Gtk.TextView):
            return current
        current = current.get_parent()
    return None


def text_from_widget(widget: Gtk.Widget | None) -> str | None:
    current = widget
    while current is not None:
        if isinstance(current, TextBox):
            buffer = current.buffer
            text = buffer.get_text(
                buffer.get_start_iter(), buffer.get_end_iter(), True
            )
            if text:
                return text
            if current.title:
                return current.title
        if isinstance(current, ImportItem):
            return current.display_name
        if isinstance(current, GraphNodeItem):
            return "\n".join(line.text for line in current.node.text_lines) or (
                current.title or current.node.detail
            )
        if isinstance(current, ShapeItem):
            return current.shape.name
        if isinstance(current, Gtk.TextView):
            buffer = current.get_buffer()
            selection = buffer.get_selection_bounds()
            if selection and not selection[0].equal(selection[1]):
                return buffer.get_text(selection[0], selection[1], True)
            text = buffer.get_text(
                buffer.get_start_iter(), buffer.get_end_iter(), True
            )
            if text:
                return text
        if isinstance(current, Gtk.Label):
            text = current.get_text().strip()
            if text:
                return text
        if isinstance(current, Gtk.Button):
            label = current.get_label()
            if label:
                return label.strip()
        current = current.get_parent()
    return None
