from __future__ import annotations

import math
import heapq
from collections import defaultdict, deque
from collections.abc import Callable
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from ...graphs import CallGraph, CallGraphBuilder
from ...graphs.call_graph import CallGraphNode
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
        self._all_nodes_selected = False
        self._pan_offset = (0.0, 0.0)
        self._drag_origin = (0.0, 0.0)
        self._routes: list[list[tuple[float, float]]] = []
        self.graph: CallGraph | None = None

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.title = Gtk.Label(label="Function Call Graph")
        self.title.set_halign(Gtk.Align.START)
        self.title.add_css_class("analysis-placeholder-title")
        self.title.set_hexpand(True)
        header.append(self.title)
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
        drag = Gtk.GestureDrag.new()
        drag.connect("drag-begin", self._on_pan_begin)
        drag.connect("drag-update", self._on_pan_update)
        self.canvas.add_controller(drag)

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
        self._all_nodes_selected = False
        if source is None or not source.strip():
            self.graph = None
            self._routes = []
            self.title.set_text("Function Call Graph")
            self._show_state("Open a source file to view its call graph.")
            return
        try:
            result = self._parser.parse(source, language=language, file_path=file_path)
            self.graph = self._builder.build(result)
        except (RuntimeError, ValueError, TypeError) as error:
            self.graph = None
            self._routes = []
            self._show_state(f"Call graph unavailable: {error}")
            return

        self.title.set_text(
            f"Function Call Graph · {file_path.name if file_path else 'Untitled source'}"
        )
        if not self.graph.nodes:
            self._routes = []
            self._show_state("No function definitions found in this source.")
            return
        self._pan_offset = (0.0, 0.0)
        self._layout_graph()
        node_by_id = {node.node_id: node for node in self.graph.nodes}
        self._routes = [
            self._edge_route(
                node_by_id[edge.source_id],
                node_by_id[edge.target_id],
                index,
                self.graph.nodes,
            )
            for index, edge in enumerate(self.graph.edges)
        ]
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
        left = min(node.x for node in self.graph.nodes)
        right = max(node.x + node.width for node in self.graph.nodes)
        top = min(node.y for node in self.graph.nodes)
        bottom = max(node.y + node.height for node in self.graph.nodes)
        viewport_width = max(260, self.scroller.get_width())
        viewport_height = max(200, self.scroller.get_height())
        padding = 80
        self.canvas.set_content_width(
            max(viewport_width, math.ceil((right - left) * self._zoom + padding))
        )
        self.canvas.set_content_height(
            max(viewport_height, math.ceil((bottom - top) * self._zoom + padding))
        )
        self.scroller.set_child(self.canvas)
        self.canvas.queue_draw()

    def _graph_origin(self) -> tuple[float, float]:
        graph = self.graph
        if graph is None or not graph.nodes:
            return 0.0, 0.0
        left = min(node.x for node in graph.nodes)
        right = max(node.x + node.width for node in graph.nodes)
        top = min(node.y for node in graph.nodes)
        bottom = max(node.y + node.height for node in graph.nodes)
        width = self.canvas.get_content_width() or self.canvas.get_width()
        height = self.canvas.get_content_height() or self.canvas.get_height()
        return (
            (width - (right - left) * self._zoom) / 2 - left * self._zoom,
            (height - (bottom - top) * self._zoom) / 2 - top * self._zoom,
        )

    def _change_zoom(self, factor: float) -> None:
        self._zoom = min(3.0, max(0.4, self._zoom * factor))
        self._render_graph()

    def zoom_in(self) -> None:
        self._change_zoom(1.25)

    def zoom_out(self) -> None:
        self._change_zoom(0.8)

    def _on_pan_begin(
        self, _gesture: Gtk.GestureDrag, _x: float, _y: float
    ) -> None:
        self._drag_origin = self._pan_offset

    def _on_pan_update(
        self, _gesture: Gtk.GestureDrag, offset_x: float, offset_y: float
    ) -> None:
        graph = self.graph
        if graph is None or not graph.nodes:
            return
        origin_x, origin_y = self._graph_origin()
        canvas_width = self.canvas.get_content_width()
        canvas_height = self.canvas.get_content_height()
        left = min(node.x for node in graph.nodes) * self._zoom + origin_x
        right = max(node.x + node.width for node in graph.nodes) * self._zoom + origin_x
        top = min(node.y for node in graph.nodes) * self._zoom + origin_y
        bottom = max(node.y + node.height for node in graph.nodes) * self._zoom + origin_y
        min_x = min(0.0, 40.0 - right)
        max_x = max(0.0, canvas_width - 40.0 - left)
        min_y = min(0.0, 40.0 - bottom)
        max_y = max(0.0, canvas_height - 40.0 - top)
        self._pan_offset = (
            min(max_x, max(min_x, self._drag_origin[0] + offset_x)),
            min(max_y, max(min_y, self._drag_origin[1] + offset_y)),
        )
        self.canvas.queue_draw()

    def _on_canvas_pressed(
        self,
        _gesture: Gtk.GestureClick,
        _press_count: int,
        x: float,
        y: float,
    ) -> None:
        node = self.node_at(x, y)
        self._all_nodes_selected = False
        self.canvas.queue_draw()
        if node is None or self._on_source_navigate is None:
            return
        self._on_source_navigate(node.source_node)

    def node_at(self, x: float, y: float) -> CallGraphNode | None:
        if self.graph is None:
            return None
        origin_x, origin_y = self._graph_origin()
        graph_x = (x - self._pan_offset[0] - origin_x) / self._zoom
        graph_y = (y - self._pan_offset[1] - origin_y) / self._zoom
        return next(
            (
                item for item in reversed(self.graph.nodes)
                if item.x <= graph_x <= item.x + item.width
                and item.y <= graph_y <= item.y + item.height
            ),
            None,
        )

    def select_all_nodes(self) -> None:
        self._all_nodes_selected = bool(self.graph and self.graph.nodes)
        self.canvas.queue_draw()

    @staticmethod
    def _connection_summary(graph: CallGraph, node_id: str) -> str:
        calls = sum(edge.source_id == node_id for edge in graph.edges)
        called_by = sum(edge.target_id == node_id for edge in graph.edges)
        return f"calls {calls} / called by {called_by}"

    @staticmethod
    def _edge_route(
        source: object,
        target: object,
        index: int,
        nodes: list[object] | None = None,
    ) -> list[tuple[float, float]]:
        source_right = source.x + source.width
        target_right = target.x + target.width
        if source.node_id == target.node_id:
            start = (source_right, source.y + source.height / 2)
            end = (source.x, source.y + source.height / 2)
        elif target.x >= source_right:
            start = (source_right, source.y + source.height / 2)
            end = (target.x, target.y + target.height / 2)
        else:
            start = (source.x, source.y + source.height / 2)
            end = (target_right, target.y + target.height / 2)

        obstacles = nodes if nodes is not None else [source, target]
        padding = 18.0
        x_values = {start[0], end[0]}
        y_values = {start[1], end[1]}
        for node in obstacles:
            x_values.update(
                (node.x - padding, node.x, node.x + node.width,
                 node.x + node.width + padding)
            )
            y_values.update(
                (node.y - padding, node.y, node.y + node.height,
                 node.y + node.height + padding, node.y + node.height / 2)
            )

        xs = sorted(x_values)
        ys = sorted(y_values)
        points = [(x, y) for y in ys for x in xs]
        point_index = {point: index for index, point in enumerate(points)}

        def inside_node(point: tuple[float, float], node: object) -> bool:
            x, y = point
            return node.x < x < node.x + node.width and node.y < y < node.y + node.height

        def segment_clear(
            first: tuple[float, float], second: tuple[float, float]
        ) -> bool:
            for node in obstacles:
                left, right = node.x, node.x + node.width
                top, bottom = node.y, node.y + node.height
                if first[1] == second[1]:
                    if top <= first[1] <= bottom and max(min(first[0], second[0]), left) < min(max(first[0], second[0]), right):
                        return False
                elif left <= first[0] <= right and max(min(first[1], second[1]), top) < min(max(first[1], second[1]), bottom):
                    return False
            return True

        valid = [
            not any(inside_node(point, node) for node in obstacles)
            or point in {start, end}
            for point in points
        ]
        start_index = point_index[start]
        end_index = point_index[end]
        distances = [math.inf] * len(points)
        previous: list[int | None] = [None] * len(points)
        distances[start_index] = 0.0
        pending = [(0.0, start_index)]
        while pending:
            distance, current = heapq.heappop(pending)
            if distance != distances[current]:
                continue
            if current == end_index:
                break
            x_index = current % len(xs)
            y_index = current // len(xs)
            neighbors = []
            if x_index > 0:
                neighbors.append(current - 1)
            if x_index + 1 < len(xs):
                neighbors.append(current + 1)
            if y_index > 0:
                neighbors.append(current - len(xs))
            if y_index + 1 < len(ys):
                neighbors.append(current + len(xs))
            for neighbor in neighbors:
                if not valid[neighbor] or not segment_clear(points[current], points[neighbor]):
                    continue
                step = abs(points[current][0] - points[neighbor][0]) + abs(points[current][1] - points[neighbor][1])
                candidate = distance + step
                if candidate < distances[neighbor]:
                    distances[neighbor] = candidate
                    previous[neighbor] = current
                    heapq.heappush(pending, (candidate, neighbor))

        if not math.isfinite(distances[end_index]):
            return [start, (start[0], source.y - padding),
                    (end[0], source.y - padding), end]
        route = []
        current: int | None = end_index
        while current is not None:
            route.append(points[current])
            current = previous[current]
        route.reverse()
        simplified = [route[0]]
        for point in route[1:]:
            if len(simplified) >= 2:
                first, middle = simplified[-2], simplified[-1]
                if (first[0] == middle[0] == point[0]) or (first[1] == middle[1] == point[1]):
                    simplified[-1] = point
                    continue
            simplified.append(point)
        return simplified

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
        context.translate(*self._pan_offset)
        context.translate(*self._graph_origin())
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
            points = self._routes[index]
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
            horizontal_segments = [
                (abs(second[0] - first[0]), first, second)
                for first, second in zip(points, points[1:])
                if first[1] == second[1]
            ]
            if horizontal_segments:
                segment_length, first, second = max(horizontal_segments, key=lambda item: item[0])
                if segment_length >= extents.width + 12:
                    label_x = (first[0] + second[0]) / 2 - extents.width / 2
                    label_y = first[1] - 6
                    context.set_source_rgba(0.65, 0.88, 0.98, 0.95)
                    context.move_to(label_x, label_y)
                    context.show_text(label)

        for node in graph.nodes:
            selected = self._all_nodes_selected
            context.set_source_rgba(
                0.97 if selected else 0.16,
                0.78 if selected else 0.48,
                0.22 if selected else 0.42,
                0.38 if selected else 0.20,
            )
            context.rectangle(node.x, node.y, node.width, node.height)
            context.fill_preserve()
            context.set_source_rgba(
                0.97 if selected else 0.16,
                0.78 if selected else 0.48,
                0.22 if selected else 0.42,
                1.0,
            )
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