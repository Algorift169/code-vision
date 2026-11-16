from __future__ import annotations

import math
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from ...dependencies import DependencyAnalyzer


@dataclass
class _DiagramNode:
    node_id: str
    label: str
    detail: str
    kind: str
    file_path: Path | None
    x: float = 0.0
    y: float = 0.0


class DependencyView(Gtk.Box):
    """Interactive project dependency diagram for the analysis panel."""

    _NODE_WIDTH = 220.0
    _NODE_HEIGHT = 68.0

    def __init__(self, on_file_navigate: Callable[[Path], None] | None = None) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.set_hexpand(True)
        self.set_vexpand(True)
        self._project_root: Path | None = None
        self._analysis = None
        self._on_file_navigate = on_file_navigate
        self._zoom = 1.0
        self._pan_offset = (0.0, 0.0)
        self._drag_origin = (0.0, 0.0)
        self._diagram_nodes: list[_DiagramNode] = []
        self._diagram_edges: list[tuple[str, str, str]] = []
        self._node_by_id: dict[str, _DiagramNode] = {}

        title = Gtk.Label(label="Dependency")
        title.add_css_class("analysis-placeholder-title")
        title.set_halign(Gtk.Align.START)
        self.append(title)

        subtitle = Gtk.Label(label="Project Dependency Graph")
        subtitle.set_halign(Gtk.Align.START)
        subtitle.set_margin_bottom(2)
        self.append(subtitle)

        self.summary_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.summary_box.set_hexpand(True)
        self.append(self.summary_box)

        self.canvas = Gtk.DrawingArea()
        self.canvas.set_name("dependency-graph-canvas")
        self.canvas.set_hexpand(True)
        self.canvas.set_vexpand(True)
        self.canvas.set_content_width(1)
        self.canvas.set_content_height(300)
        self.canvas.set_draw_func(self._draw_graph)
        click = Gtk.GestureClick.new()
        click.connect("pressed", self._on_canvas_pressed)
        self.canvas.add_controller(click)
        drag = Gtk.GestureDrag.new()
        drag.connect("drag-begin", self._on_pan_begin)
        drag.connect("drag-update", self._on_pan_update)
        self.canvas.add_controller(drag)

        self.scroller = Gtk.ScrolledWindow()
        self.scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.scroller.set_hexpand(True)
        self.scroller.set_vexpand(True)
        self.scroller.set_child(self.canvas)
        self.empty_label = Gtk.Label(
            label="Open a project folder to inspect its dependency graph."
        )
        self.empty_label.set_wrap(True)
        self.empty_label.set_halign(Gtk.Align.CENTER)
        self.empty_label.set_valign(Gtk.Align.CENTER)
        self.scroller.set_child(self.empty_label)
        self.append(self.scroller)

        self._empty_state()

    def set_project_root(self, project_root: Path | None) -> None:
        self._project_root = project_root
        if project_root is None:
            self._analysis = None
            self._empty_state()
            return
        try:
            self._analysis = DependencyAnalyzer().analyze(project_root)
        except (FileNotFoundError, OSError, ValueError) as error:
            self._analysis = None
            self._error_state(str(error))
            return
        self._render_analysis()

    def _empty_state(self) -> None:
        for child in list(self.summary_box):
            self.summary_box.remove(child)
        self._diagram_nodes = []
        self._diagram_edges = []
        self._node_by_id = {}
        self.empty_label.set_text("Open a project folder to inspect its dependency graph.")
        self.scroller.set_child(self.empty_label)

    def _error_state(self, message: str) -> None:
        for child in list(self.summary_box):
            self.summary_box.remove(child)
        self._diagram_nodes = []
        self._diagram_edges = []
        self._node_by_id = {}
        self.empty_label.set_text(f"Dependency graph unavailable: {message}")
        self.scroller.set_child(self.empty_label)

    def _render_analysis(self) -> None:
        if self._analysis is None:
            self._empty_state()
            return

        for child in list(self.summary_box):
            self.summary_box.remove(child)

        metrics = [
            ("Files", str(self._analysis.summary["total_files"])),
            ("Edges", str(self._analysis.summary["total_edges"])),
            ("Internal", str(self._analysis.summary["internal_edges"])),
            ("Stdlib", str(self._analysis.summary["stdlib_edges"])),
            ("Cycles", str(self._analysis.summary["cycle_count"])),
        ]

        for label_text, value in metrics:
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            card.add_css_class("complexity-summary-card")
            card.set_hexpand(True)
            name = Gtk.Label(label=label_text)
            name.add_css_class("complexity-meta-label")
            count = Gtk.Label(label=value)
            count.add_css_class("complexity-summary-value")
            card.append(name)
            card.append(count)
            self.summary_box.append(card)

        self._build_diagram()
        self._layout_diagram()
        if not self._diagram_edges:
            self.empty_label.set_text("No dependencies detected. Project files are shown below.")
        self._render_canvas()

    def _build_diagram(self) -> None:
        graph = self._analysis.graph
        file_nodes = {
            node.node_id: _DiagramNode(
                node_id=node.node_id,
                label=node.display_name,
                detail=node.relative_path,
                kind="internal",
                file_path=node.file_path,
            )
            for node in graph.nodes
        }
        self._diagram_nodes = list(file_nodes.values())
        self._node_by_id = dict(file_nodes)
        self._diagram_edges = []

        external_nodes: dict[str, _DiagramNode] = {}
        for edge in graph.edges:
            target_id = edge.target
            if target_id not in self._node_by_id:
                target_id = f"{edge.kind}:{edge.target}"
                if target_id not in external_nodes:
                    external_nodes[target_id] = _DiagramNode(
                        node_id=target_id,
                        label=edge.target.rsplit("/", 1)[-1],
                        detail=edge.kind.upper(),
                        kind=edge.kind,
                        file_path=None,
                    )
            self._diagram_edges.append((edge.source, target_id, edge.kind))

        self._diagram_nodes.extend(external_nodes.values())
        self._node_by_id.update(external_nodes)

    def _layout_diagram(self) -> None:
        if not self._diagram_nodes:
            return
        incoming = {node.node_id: 0 for node in self._diagram_nodes}
        adjacency: dict[str, set[str]] = defaultdict(set)
        for source_id, target_id, _kind in self._diagram_edges:
            if source_id in incoming and target_id in incoming:
                adjacency[source_id].add(target_id)
                incoming[target_id] += 1

        ranks = {node_id: 0 for node_id, count in incoming.items() if count == 0}
        pending = deque(ranks)
        while pending:
            source_id = pending.popleft()
            for target_id in sorted(adjacency[source_id]):
                candidate_rank = min(ranks[source_id] + 1, 5)
                if candidate_rank > ranks.get(target_id, -1):
                    ranks[target_id] = candidate_rank
                    pending.append(target_id)
        for node in self._diagram_nodes:
            ranks.setdefault(node.node_id, 0)

        groups: dict[int, list[_DiagramNode]] = defaultdict(list)
        for node in self._diagram_nodes:
            groups[ranks[node.node_id]].append(node)
        for rank, nodes in groups.items():
            nodes.sort(key=lambda item: (item.kind != "internal", item.detail.lower()))
            for row, node in enumerate(nodes):
                node.x = 36.0 + rank * 330.0
                node.y = 36.0 + row * 104.0

    def _render_canvas(self) -> None:
        if not self._diagram_nodes:
            self.empty_label.set_text("No source files found in this project.")
            self.scroller.set_child(self.empty_label)
            return
        self.scroller.set_child(self.canvas)
        left = min(node.x for node in self._diagram_nodes)
        top = min(node.y for node in self._diagram_nodes)
        right = max(node.x + self._NODE_WIDTH for node in self._diagram_nodes)
        bottom = max(node.y + self._NODE_HEIGHT for node in self._diagram_nodes)
        width = max(300, self.scroller.get_width())
        height = max(260, self.scroller.get_height())
        self.canvas.set_content_width(max(width, math.ceil((right - left + 72) * self._zoom)))
        self.canvas.set_content_height(max(height, math.ceil((bottom - top + 72) * self._zoom)))
        self.canvas.queue_draw()

    def zoom_in(self) -> None:
        self._zoom = min(2.5, self._zoom * 1.2)
        self._render_canvas()

    def zoom_out(self) -> None:
        self._zoom = max(0.45, self._zoom / 1.2)
        self._render_canvas()

    def _graph_origin(self) -> tuple[float, float]:
        if not self._diagram_nodes:
            return 0.0, 0.0
        left = min(node.x for node in self._diagram_nodes)
        top = min(node.y for node in self._diagram_nodes)
        right = max(node.x + self._NODE_WIDTH for node in self._diagram_nodes)
        bottom = max(node.y + self._NODE_HEIGHT for node in self._diagram_nodes)
        width = self.canvas.get_content_width() or self.canvas.get_width()
        height = self.canvas.get_content_height() or self.canvas.get_height()
        return (
            (width - (right - left) * self._zoom) / 2 - left * self._zoom,
            (height - (bottom - top) * self._zoom) / 2 - top * self._zoom,
        )

    def _on_pan_begin(self, _gesture: Gtk.GestureDrag, _x: float, _y: float) -> None:
        self._drag_origin = self._pan_offset

    def _on_pan_update(
        self, _gesture: Gtk.GestureDrag, offset_x: float, offset_y: float
    ) -> None:
        self._pan_offset = (
            self._drag_origin[0] + offset_x,
            self._drag_origin[1] + offset_y,
        )
        self.canvas.queue_draw()

    def _on_canvas_pressed(
        self,
        _gesture: Gtk.GestureClick,
        _press_count: int,
        x: float,
        y: float,
    ) -> None:
        if self._on_file_navigate is None:
            return
        origin_x, origin_y = self._graph_origin()
        graph_x = (x - self._pan_offset[0] - origin_x) / self._zoom
        graph_y = (y - self._pan_offset[1] - origin_y) / self._zoom
        for node in reversed(self._diagram_nodes):
            if (
                node.file_path is not None
                and node.x <= graph_x <= node.x + self._NODE_WIDTH
                and node.y <= graph_y <= node.y + self._NODE_HEIGHT
            ):
                self._on_file_navigate(node.file_path)
                return

    @staticmethod
    def _draw_arrow(context: object, start: tuple[float, float], end: tuple[float, float]) -> None:
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
        _width: int,
        _height: int,
        *_args: object,
    ) -> None:
        if not self._diagram_nodes:
            return
        context.save()
        context.translate(*self._pan_offset)
        context.translate(*self._graph_origin())
        context.scale(self._zoom, self._zoom)
        context.select_font_face("Sans", 0, 0)

        for source_id, target_id, kind in self._diagram_edges:
            source = self._node_by_id.get(source_id)
            target = self._node_by_id.get(target_id)
            if source is None or target is None:
                continue
            color = self._kind_color(kind)
            start = (source.x + self._NODE_WIDTH, source.y + self._NODE_HEIGHT / 2)
            end = (target.x, target.y + self._NODE_HEIGHT / 2)
            if target.x <= source.x:
                start = (source.x, source.y + self._NODE_HEIGHT / 2)
                end = (target.x + self._NODE_WIDTH, target.y + self._NODE_HEIGHT / 2)
            bend = max(44.0, abs(end[0] - start[0]) * 0.42)
            direction = 1.0 if end[0] >= start[0] else -1.0
            context.set_source_rgba(*color, 0.82)
            context.set_line_width(2.0)
            context.move_to(*start)
            context.curve_to(
                start[0] + bend * direction,
                start[1],
                end[0] - bend * direction,
                end[1],
                *end,
            )
            context.stroke()
            context.move_to(*end)
            self._draw_arrow(context, (end[0] - direction, end[1]), end)

        foreground = self.canvas.get_style_context().get_color()
        context.select_font_face("Sans", 0, 0)
        for node in self._diagram_nodes:
            color = self._kind_color(node.kind)
            context.set_source_rgba(*color, 0.18)
            context.rectangle(node.x, node.y, self._NODE_WIDTH, self._NODE_HEIGHT)
            context.fill_preserve()
            context.set_source_rgba(*color, 0.92)
            context.set_line_width(1.6)
            context.stroke()
            context.set_source_rgba(
                foreground.red, foreground.green, foreground.blue, foreground.alpha
            )
            context.set_font_size(13)
            context.move_to(node.x + 12, node.y + 27)
            context.show_text(self._fit_label(node.label, 25))
            context.set_font_size(10)
            context.set_source_rgba(
                foreground.red, foreground.green, foreground.blue, foreground.alpha * 0.78
            )
            context.move_to(node.x + 12, node.y + 49)
            context.show_text(self._fit_label(node.detail, 31))
        context.restore()

    @staticmethod
    def _fit_label(value: str, max_length: int) -> str:
        if len(value) <= max_length:
            return value
        return value[: max_length - 3] + "..."

    @staticmethod
    def _kind_color(kind: str) -> tuple[float, float, float]:
        return {
            "internal": (0.12, 0.66, 0.49),
            "stdlib": (0.20, 0.55, 0.86),
            "external": (0.89, 0.57, 0.20),
            "unresolved": (0.86, 0.30, 0.32),
        }.get(kind, (0.48, 0.55, 0.62))


from .dependency_workspace import DependencyView
