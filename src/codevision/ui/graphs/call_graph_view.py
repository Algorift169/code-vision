from __future__ import annotations

import math
from collections import defaultdict, deque
from collections.abc import Callable
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from ...graphs import CallGraph, CallGraphBuilder
from ...model import ASTNode
from ...parser import SourceParser


class CallGraphView(Gtk.Box):
    """Display function definitions and resolved in-file call relationships."""

    def __init__(
        self,
        on_source_navigate: Callable[[ASTNode], None] | None = None,
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_hexpand(True)
        self.set_vexpand(True)
        self._parser = SourceParser()
        self._builder = CallGraphBuilder()
        self._on_source_navigate = on_source_navigate
        self._zoom = 1.0
        self.graph: CallGraph | None = None

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.title = Gtk.Label(label="Function Call Graph")
        self.title.set_halign(Gtk.Align.START)
        self.title.add_css_class("analysis-placeholder-title")
        self.title.set_hexpand(True)
        header.append(self.title)
        self.zoom_out_button = Gtk.Button.new_from_icon_name("zoom-out-symbolic")
        self.zoom_out_button.set_tooltip_text("Zoom out")
        self.zoom_out_button.connect("clicked", lambda _button: self._change_zoom(0.8))
        header.append(self.zoom_out_button)
        self.zoom_in_button = Gtk.Button.new_from_icon_name("zoom-in-symbolic")
        self.zoom_in_button.set_tooltip_text("Zoom in")
        self.zoom_in_button.connect("clicked", lambda _button: self._change_zoom(1.25))
        header.append(self.zoom_in_button)
        self.append(header)

        self.canvas = Gtk.DrawingArea()
        self.canvas.set_name("call-graph-canvas")
        self.canvas.set_hexpand(True)
        self.canvas.set_vexpand(True)
        self.canvas.set_content_width(1)
        self.canvas.set_content_height(240)
        self.canvas.set_draw_func(self._draw_graph)
        click = Gtk.GestureClick.new()
        click.connect("pressed", self._on_canvas_pressed)
        self.canvas.add_controller(click)

        self.scroller = Gtk.ScrolledWindow()
        self.scroller.set_policy(
            Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC
        )
        self.scroller.set_hexpand(True)
        self.scroller.set_vexpand(True)
        self.scroller.set_child(self.canvas)
        self._state = Gtk.Label(label="Open a source file to view its call graph.")
        self._state.set_wrap(True)
        self._state.set_halign(Gtk.Align.CENTER)
        self._state.set_valign(Gtk.Align.CENTER)
        self.scroller.set_child(self._state)
        self.append(self.scroller)

    def set_source(
        self,
        source: str | None,
        file_path: Path | None,
        language: str | None = None,
    ) -> None:
        if source is None or not source.strip():
            self.graph = None
            self.title.set_text("Function Call Graph")
            self._show_state("Open a source file to view its call graph.")
            return
        try:
            result = self._parser.parse(source, language=language, file_path=file_path)
            self.graph = self._builder.build(result)
        except (RuntimeError, ValueError, TypeError) as error:
            self.graph = None
            self._show_state(f"Call graph unavailable: {error}")
            return

        self.title.set_text(
            f"Function Call Graph · {file_path.name if file_path else 'Untitled source'}"
        )
        if not self.graph.nodes:
            self._show_state("No function definitions found in this source.")
            return
        self._layout_graph()
        self._render_graph()

    def _show_state(self, message: str) -> None:
        self._state.set_text(message)
        self.scroller.set_child(self._state)

    @staticmethod
    def _column_step(graph: CallGraph) -> float:
        if not graph.edges:
            return 220.0
        label_width = max((len(edge.label) * 7.5 + 60.0 for edge in graph.edges), default=220.0)
        node_map = {node.node_id: node for node in graph.nodes}
        actual_gap = 0.0
        for edge in graph.edges:
            source = node_map.get(edge.source_id)
            target = node_map.get(edge.target_id)
            if source is None or target is None:
                continue
            gap = max(0.0, target.x - source.x - source.width)
            actual_gap = max(actual_gap, gap)
        return max(220.0, label_width, actual_gap + 80.0)

    def _layout_graph(self) -> None:
        graph = self.graph
        if graph is None:
            return
        adjacency: dict[str, list[str]] = defaultdict(list)
        incoming = {node.node_id: 0 for node in graph.nodes}
        for edge in graph.edges:
            adjacency[edge.source_id].append(edge.target_id)
            incoming[edge.target_id] += 1
        depths: dict[str, int] = {}
        pending = deque(
            node.node_id for node in graph.nodes if incoming[node.node_id] == 0
        )
        for node_id in pending:
            depths[node_id] = 0
        while pending:
            source_id = pending.popleft()
            for target_id in adjacency[source_id]:
                if target_id not in depths:
                    depths[target_id] = depths[source_id] + 1
                    pending.append(target_id)
        for node in graph.nodes:
            if node.node_id in depths:
                continue
            depths[node.node_id] = max(depths.values(), default=-1) + 1
            pending.append(node.node_id)
            while pending:
                source_id = pending.popleft()
                for target_id in adjacency[source_id]:
                    if target_id not in depths:
                        depths[target_id] = depths[source_id] + 1
                        pending.append(target_id)

        column_step = self._column_step(graph)
        rows_by_depth: dict[int, int] = defaultdict(int)
        for node in sorted(
            graph.nodes, key=lambda item: item.source_node.location.start_line
        ):
            depth = depths[node.node_id]
            node.x = 20 + depth * column_step
            node.y = 20 + rows_by_depth[depth] * 90
            rows_by_depth[depth] += 1

        actual_gap = 0.0
        node_map = {node.node_id: node for node in graph.nodes}
        for edge in graph.edges:
            source = node_map.get(edge.source_id)
            target = node_map.get(edge.target_id)
            if source is None or target is None:
                continue
            actual_gap = max(actual_gap, max(0.0, target.x - source.x - source.width))
        if actual_gap > 0:
            column_step = max(column_step, actual_gap + 40.0)
            for node in graph.nodes:
                node.x = 20 + depths[node.node_id] * column_step

    def _render_graph(self) -> None:
        if self.graph is None or not self.graph.nodes:
            return
        right = max(node.x + node.width for node in self.graph.nodes)
        bottom = max(node.y + node.height for node in self.graph.nodes)
        self.canvas.set_content_width(
            max(260, math.ceil((right + 18) * self._zoom))
        )
        self.canvas.set_content_height(
            max(200, math.ceil((bottom + 18) * self._zoom))
        )
        self.scroller.set_child(self.canvas)
        self.canvas.queue_draw()

    def _change_zoom(self, factor: float) -> None:
        self._zoom = min(3.0, max(0.4, self._zoom * factor))
        self._render_graph()

    def _on_canvas_pressed(
        self,
        _gesture: Gtk.GestureClick,
        _press_count: int,
        x: float,
        y: float,
    ) -> None:
        if self.graph is None or self._on_source_navigate is None:
            return
        x /= self._zoom
        y /= self._zoom
        node = next(
            (
                item for item in reversed(self.graph.nodes)
                if item.x <= x <= item.x + item.width
                and item.y <= y <= item.y + item.height
            ),
            None,
        )
        if node is not None:
            self._on_source_navigate(node.source_node)

    @staticmethod
    def _connection_summary(graph: CallGraph, node_id: str) -> str:
        calls = sum(edge.source_id == node_id for edge in graph.edges)
        called_by = sum(edge.target_id == node_id for edge in graph.edges)
        return f"calls {calls} / called by {called_by}"

    @staticmethod
    def _edge_route(
        source: object, target: object, index: int
    ) -> list[tuple[float, float]]:
        start_x = source.x + source.width
        end_x = target.x
        start = (start_x, source.y + source.height / 2)
        end = (end_x, target.y + target.height / 2)
        pipe_gap = 18.0
        lane_y = min(source.y, target.y) - 18.0 - (index % 5) * 8.0
        if source.node_id == target.node_id:
            lane_x = start_x + pipe_gap + 14.0
            return [
                start,
                (lane_x, start[1]),
                (lane_x, source.y - 28.0),
                (source.x + source.width / 2, source.y - 28.0),
                (source.x + source.width / 2, source.y),
            ]

        if end_x >= start_x:
            pipe_start = start_x + pipe_gap
            pipe_end = end_x - pipe_gap
            if pipe_end <= pipe_start:
                pipe_end = start_x + (end_x - start_x) / 2.0
                pipe_start = pipe_end
            return [
                (start_x, start[1]),
                (pipe_start, start[1]),
                (pipe_start, lane_y),
                (pipe_end, lane_y),
                (pipe_end, end[1]),
                end,
            ]

        pipe_start = start_x + pipe_gap
        pipe_end = end_x - pipe_gap
        return [
            (start_x, start[1]),
            (pipe_start, start[1]),
            (pipe_start, lane_y),
            (pipe_end, lane_y),
            (pipe_end, end[1]),
            end,
        ]

    @staticmethod
    def _draw_arrow(
        context: object,
        start: tuple[float, float],
        end: tuple[float, float],
    ) -> None:
        angle = math.atan2(end[1] - start[1], end[0] - start[0])
        base_x = end[0] - 10 * math.cos(angle)
        base_y = end[1] - 10 * math.sin(angle)
        context.move_to(*end)
        context.line_to(base_x + 5 * math.sin(angle), base_y - 5 * math.cos(angle))
        context.line_to(base_x - 5 * math.sin(angle), base_y + 5 * math.cos(angle))
        context.close_path()
        context.fill()

    def _draw_graph(
        self,
        _area: Gtk.DrawingArea,
        context: object,
        width: int,
        height: int,
        *_args: object,
    ) -> None:
        graph = self.graph
        if graph is None:
            return
        context.save()
        context.scale(self._zoom, self._zoom)
        context.select_font_face("Sans", 0, 0)
        context.set_font_size(12)
        foreground = self.canvas.get_style_context().get_color()
        context.set_source_rgba(
            foreground.red, foreground.green, foreground.blue, foreground.alpha
        )
        node_by_id = {node.node_id: node for node in graph.nodes}
        for index, edge in enumerate(graph.edges):
            source = node_by_id.get(edge.source_id)
            target = node_by_id.get(edge.target_id)
            if source is None or target is None:
                continue
            points = self._edge_route(source, target, index)
            context.set_source_rgba(0.08, 0.74, 0.96, 0.95)
            context.set_line_width(3.0)
            context.move_to(*points[0])
            for point in points[1:]:
                context.line_to(*point)
            context.stroke()
            start, end = points[-2], points[-1]
            self._draw_arrow(context, start, end)
            label = edge.label
            extents = context.text_extents(label)
            label_x = (points[1][0] + points[-2][0]) / 2 - extents.width / 2
            label_y = (points[1][1] + points[-2][1]) / 2 - 14
            context.set_source_rgba(0.04, 0.62, 0.92, 0.9)
            context.rectangle(
                label_x - 4, label_y - 12, extents.width + 8, 17
            )
            context.fill()
            context.set_source_rgba(1.0, 1.0, 1.0, 1.0)
            context.move_to(label_x, label_y)
            context.show_text(label)

        for node in graph.nodes:
            context.set_source_rgba(0.16, 0.48, 0.42, 0.20)
            context.rectangle(node.x, node.y, node.width, node.height)
            context.fill_preserve()
            context.set_source_rgba(0.16, 0.48, 0.42, 1.0)
            context.set_line_width(1.8)
            context.stroke()
            context.set_source_rgba(
                foreground.red, foreground.green, foreground.blue, foreground.alpha
            )
            context.move_to(node.x + 12, node.y + 29)
            context.show_text(node.name)
            context.move_to(node.x + 12, node.y + 50)
            context.show_text(f"line {node.source_node.location.start_line}")
            context.set_font_size(10)
            context.move_to(node.x + 12, node.y + 65)
            context.show_text(self._connection_summary(graph, node.node_id))
            context.set_font_size(12)
        context.restore()


__all__ = ["CallGraphView"]