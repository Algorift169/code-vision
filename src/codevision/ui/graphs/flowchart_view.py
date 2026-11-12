from __future__ import annotations

from pathlib import Path

import math

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from ...graphs import FlowchartBuilder, FlowchartGraph, GraphLayout
from ...parser import SourceParser


class FlowchartView(Gtk.Box):
    """Render an AST-derived flowchart on a scrollable Cairo canvas."""

    _NODE_COLORS = {
        "start": (0.12, 0.63, 0.53),
        "end": (0.12, 0.63, 0.53),
        "process": (0.24, 0.52, 0.88),
        "decision": (0.94, 0.63, 0.12),
        "loop": (0.94, 0.63, 0.12),
        "function": (0.58, 0.38, 0.82),
        "input": (0.18, 0.66, 0.42),
        "output": (0.18, 0.66, 0.42),
        "return": (0.87, 0.34, 0.38),
        "break": (0.87, 0.34, 0.38),
        "continue": (0.87, 0.34, 0.38),
        "exception": (0.89, 0.43, 0.18),
        "merge": (0.35, 0.60, 0.68),
        "connector": (0.35, 0.60, 0.68),
    }
    _EDGE_COLOR = (0.24, 0.55, 0.78)
    _YES_COLOR = (0.15, 0.62, 0.40)
    _NO_COLOR = (0.82, 0.31, 0.35)

    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.set_hexpand(True)
        self.set_vexpand(True)
        self._parser = SourceParser()
        self._builder = FlowchartBuilder()
        self.graph: FlowchartGraph | None = None
        self.canvas = Gtk.DrawingArea()
        self.canvas.set_name("flowchart-canvas")
        self.canvas.add_css_class("flowchart-canvas")
        self.canvas.set_content_width(1)
        self.canvas.set_content_height(320)
        self.canvas.set_hexpand(True)
        self.canvas.set_vexpand(True)
        self.canvas.set_draw_func(self._draw_graph)
        self.scroller = Gtk.ScrolledWindow()
        self.scroller.set_policy(
            Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC
        )
        self.scroller.set_hexpand(True)
        self.scroller.set_vexpand(True)
        self.scroller.set_child(self.canvas)
        self._empty_label = Gtk.Label(label="Flowchart")
        self._empty_label.set_halign(Gtk.Align.CENTER)
        self._empty_label.set_valign(Gtk.Align.CENTER)
        self._empty_label.set_wrap(True)
        self.scroller.set_child(self._empty_label)
        self.append(self.scroller)

    def set_source(
        self,
        source: str | None,
        file_path: Path | None,
        language: str | None = None,
    ) -> None:
        if source is None or not source.strip():
            self._empty_label.set_text("Flowchart")
            self.graph = None
            self.scroller.set_child(self._empty_label)
            return

        try:
            result = self._parser.parse(source, language=language, file_path=file_path)
            graph = self._builder.build(result, source=source)
            self.graph = GraphLayout.layout(graph)
        except (RuntimeError, ValueError, TypeError) as error:
            self.graph = None
            label = Gtk.Label(label=f"Flowchart unavailable: {error}")
            label.set_wrap(True)
            label.set_halign(Gtk.Align.START)
            self.scroller.set_child(label)
            return

        if not self.graph.nodes:
            self.scroller.set_child(self._empty_label)
            return

        max_y = max(node.y + node.height for node in self.graph.nodes)
        self.canvas.set_content_width(1)
        self.canvas.set_content_height(max(320, math.ceil(max_y + 40)))
        self.scroller.set_child(self.canvas)
        self.canvas.queue_draw()

    def _draw_graph(
        self,
        _area: Gtk.DrawingArea,
        context: object,
        width: int,
        height: int,
        *_args: object,
    ) -> None:
        context.set_line_width(1.6)
        foreground = self.canvas.get_style_context().get_color()
        context.set_source_rgba(
            foreground.red, foreground.green, foreground.blue, foreground.alpha
        )

        graph = self.graph
        if graph is None:
            return

        node_by_id = {node.node_id: node for node in graph.nodes}
        graph_right = max(node.x + node.width for node in graph.nodes)
        graph_left = min(node.x for node in graph.nodes)
        context.save()
        scale, origin_x = self._graph_transform(graph, width)
        context.translate(origin_x, 16)
        context.scale(scale, scale)
        for edge_index, edge in enumerate(graph.edges):
            source = node_by_id.get(edge.source_id)
            target = node_by_id.get(edge.target_id)
            if source is None or target is None:
                continue
            points, arrow = self._edge_route(
                graph.nodes,
                source,
                target,
                graph_left,
                graph_right,
                edge_index,
            )
            edge_color = (
                self._YES_COLOR
                if edge.branch_label and edge.branch_label.lower() == "yes"
                else self._NO_COLOR
                if edge.branch_label and edge.branch_label.lower() == "no"
                else self._EDGE_COLOR
            )
            context.set_source_rgba(*edge_color, 0.95)
            context.set_line_width(2.2)
            context.move_to(*points[0])
            for point in points[1:]:
                context.line_to(*point)
            context.stroke()
            self._draw_arrow(context, *arrow)
            if edge.branch_label:
                label_x, label_y = points[len(points) // 2]
                context.move_to(label_x + 5, label_y - 4)
                context.show_text(edge.branch_label.upper())

        foreground = self.canvas.get_style_context().get_color()
        context.set_source_rgba(
            foreground.red, foreground.green, foreground.blue, foreground.alpha
        )
        for node in graph.nodes:
            self._draw_node(context, node)
        context.restore()

    @staticmethod
    def _graph_transform(
        graph: FlowchartGraph, canvas_width: int
    ) -> tuple[float, float]:
        left = min(node.x for node in graph.nodes)
        right = max(node.x + node.width for node in graph.nodes)
        rail_padding = 70.0
        graph_width = right - left
        scale = min(
            1.0,
            max(0.1, (canvas_width - 32.0) / (graph_width + rail_padding * 2)),
        )
        origin_x = (canvas_width - graph_width * scale) / 2 - left * scale
        return scale, origin_x

    @staticmethod
    def _edge_route(
        nodes: list[object],
        source: object,
        target: object,
        graph_left: float,
        graph_right: float,
        edge_index: int,
    ) -> tuple[list[tuple[float, float]], tuple[float, float]]:
        source_center = source.x + source.width / 2
        target_center = target.x + target.width / 2
        start_y = source.y + source.height
        end_y = target.y
        blocked = any(
            node.node_id not in {source.node_id, target.node_id}
            and node.x < source_center < node.x + node.width
            and start_y < node.y + node.height
            and end_y > node.y
            for node in nodes
        )
        if abs(source_center - target_center) < 2 and not blocked and end_y > start_y:
            return [(source_center, start_y), (target_center, end_y - 9)], (
                target_center,
                end_y - 2,
            )

        source_y = source.y + source.height / 2
        left_is_clear = not any(
            node.node_id not in {source.node_id, target.node_id}
            and node.y <= source_y <= node.y + node.height
            and node.x < source.x
            for node in nodes
        )
        use_left = left_is_clear and source.x <= target.x
        if use_left:
            source_x = source.x
            target_x = target.x + target.width / 2
            lane_x = graph_left - 22.0 - (edge_index % 5) * 9.0
            approach_y = end_y - 14.0
            return [
                (source_x, source_y),
                (lane_x, source_y),
                (lane_x, approach_y),
                (target_x, approach_y),
                (target_x, end_y - 9.0),
            ], (target_x, end_y - 2.0)

        source_x = source.x + source.width
        target_x = target.x + target.width / 2
        lane_x = graph_right + 22.0 + (edge_index % 5) * 9.0
        approach_y = end_y - 14.0
        return [
            (source_x, source_y),
            (lane_x, source_y),
            (lane_x, approach_y),
            (target_x, approach_y),
            (target_x, end_y - 9.0),
        ], (target_x, end_y - 2.0)

    @staticmethod
    def _draw_arrow(context: object, x: float, y: float) -> None:
        context.move_to(x, y)
        context.line_to(x - 5, y - 9)
        context.line_to(x + 5, y - 9)
        context.close_path()
        context.fill()

    def _draw_node(self, context: object, node: object) -> None:
        x, y = node.x, node.y
        width, height = node.width, node.height
        kind = node.kind.value

        context.save()
        color = self._NODE_COLORS.get(kind, self._NODE_COLORS["process"])
        context.set_source_rgba(*color, 0.20)
        context.set_line_width(2.0)
        if kind in {"start", "end"}:
            context.arc(x + width / 2, y + height / 2, height / 2, 0, math.tau)
        elif kind in {"decision", "loop"}:
            context.move_to(x + width / 2, y)
            context.line_to(x + width, y + height / 2)
            context.line_to(x + width / 2, y + height)
            context.line_to(x, y + height / 2)
            context.close_path()
        elif kind in {"input", "output"}:
            context.move_to(x + 16, y)
            context.line_to(x + width, y)
            context.line_to(x + width - 16, y + height)
            context.line_to(x, y + height)
            context.close_path()
        elif kind == "exception":
            context.move_to(x + 18, y)
            context.line_to(x + width - 18, y)
            context.line_to(x + width, y + height / 2)
            context.line_to(x + width - 18, y + height)
            context.line_to(x + 18, y + height)
            context.line_to(x, y + height / 2)
            context.close_path()
        elif kind in {"merge", "connector"}:
            context.arc(x + width / 2, y + height / 2, min(width, height) / 5, 0, math.tau)
        else:
            context.rectangle(x, y, width, height)
        context.fill_preserve()
        context.set_source_rgba(*color, 1.0)
        context.stroke()

        foreground = self.canvas.get_style_context().get_color()
        context.set_source_rgba(
            foreground.red, foreground.green, foreground.blue, foreground.alpha
        )
        lines = node.metadata.get("display_lines") or [node.label]
        line_height = 14.0
        first_baseline = y + (height - line_height * len(lines)) / 2 + 11.0
        for line_index, line in enumerate(lines):
            extents = context.text_extents(line)
            text_x = x + (width - extents.width) / 2 - extents.x_bearing
            text_y = first_baseline + line_index * line_height
            context.move_to(text_x, text_y)
            context.show_text(line)
        context.restore()


__all__ = ["FlowchartView"]
