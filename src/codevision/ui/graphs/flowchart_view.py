from __future__ import annotations

import math
from collections.abc import Callable
from pathlib import Path
from typing import ClassVar

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from ...graphs import (
    FlowchartBuilder,
    FlowchartGraph,
    FlowchartNodeKind,
    GraphExporter,
    GraphLayout,
)
from ...model import ASTNode, ASTResult
from ...parser import LanguageRegistry, SourceParser


class FlowchartView(Gtk.Box):
    """Render an AST-derived flowchart on a scrollable Cairo canvas."""

    _NODE_COLORS: ClassVar[dict[str, tuple[float, float, float]]] = {
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

    def __init__(
        self,
        on_source_navigate: Callable[[ASTNode], None] | None = None,
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.set_hexpand(True)
        self.set_vexpand(True)
        self._parser = SourceParser()
        self._builder = FlowchartBuilder()
        self._exporter = GraphExporter()
        self._on_source_navigate = on_source_navigate
        self._result: ASTResult | None = None
        self._graphs: list[FlowchartGraph] = []
        self._source: str | None = None
        self._file_path: Path | None = None
        self._language: str | None = None
        self._selected_node_id: str | None = None
        self._zoom = 1.0
        self._drag_origin = (0.0, 0.0)
        self.graph: FlowchartGraph | None = None

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        title = Gtk.Label(label="Flowchart")
        title.set_halign(Gtk.Align.START)
        title.set_hexpand(True)
        header.append(title)
        self._file_label = Gtk.Label(label="No source")
        self._file_label.set_ellipsize(3)
        header.append(self._file_label)
        self.function_selector = Gtk.DropDown.new_from_strings(["Program"])
        self.function_selector.set_visible(False)
        self.function_selector.connect("notify::selected", self._on_function_selected)
        header.append(self.function_selector)
        self.refresh_button = Gtk.Button.new_from_icon_name("view-refresh-symbolic")
        self.refresh_button.set_tooltip_text("Refresh flowchart")
        self.refresh_button.connect("clicked", self._on_refresh_clicked)
        header.append(self.refresh_button)
        self.zoom_out_button = Gtk.Button.new_from_icon_name("zoom-out-symbolic")
        self.zoom_out_button.set_tooltip_text("Zoom out")
        self.zoom_out_button.connect("clicked", lambda _button: self._change_zoom(0.8))
        header.append(self.zoom_out_button)
        self.zoom_in_button = Gtk.Button.new_from_icon_name("zoom-in-symbolic")
        self.zoom_in_button.set_tooltip_text("Zoom in")
        self.zoom_in_button.connect("clicked", lambda _button: self._change_zoom(1.25))
        header.append(self.zoom_in_button)
        self.fit_button = Gtk.Button.new_from_icon_name("zoom-fit-best-symbolic")
        self.fit_button.set_tooltip_text("Fit graph")
        self.fit_button.connect("clicked", self._fit_graph)
        header.append(self.fit_button)
        self.export_button = Gtk.MenuButton()
        self.export_button.set_child(Gtk.Image.new_from_icon_name("document-save-symbolic"))
        self.export_button.set_tooltip_text("Export flowchart")
        export_popover = Gtk.Popover()
        export_actions = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        for file_type in ("svg", "png", "pdf"):
            button = Gtk.Button(label=f"Export {file_type.upper()}")
            button.connect("clicked", self._on_export_clicked, file_type)
            export_actions.append(button)
        export_popover.set_child(export_actions)
        self.export_button.set_popover(export_popover)
        header.append(self.export_button)
        self._status_label = Gtk.Label(label="")
        self._status_label.set_halign(Gtk.Align.END)
        header.append(self._status_label)
        self.append(header)

        self.canvas = Gtk.DrawingArea()
        self.canvas.set_name("flowchart-canvas")
        self.canvas.add_css_class("flowchart-canvas")
        self.canvas.set_content_width(1)
        self.canvas.set_content_height(320)
        self.canvas.set_hexpand(True)
        self.canvas.set_vexpand(True)
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
        self._empty_label = Gtk.Label(
            label="Open a supported source file to view its flowchart."
        )
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
        self._source = source
        self._file_path = file_path
        self._language = language
        self._selected_node_id = None
        if source is None or not source.strip():
            self._file_label.set_text("No source")
            self._empty_label.set_text(
                "Open a supported source file to view its flowchart."
            )
            self._graphs = []
            self._result = None
            self.graph = None
            self.scroller.set_child(self._empty_label)
            return

        try:
            language_info = LanguageRegistry.resolve(language, file_path)
            if language_info is None or "flowchart" not in language_info.capabilities:
                name = language_info.display_name if language_info else language or "source"
                raise ValueError(f"Flowcharts are not supported for {name}.")
            result = self._parser.parse(source, language=language, file_path=file_path)
            graphs = self._builder.build_all(result, source=source)
            for graph in graphs:
                GraphLayout.layout(graph)
                validation = graph.validate()
                if not validation.valid:
                    raise ValueError("; ".join(validation.issues))
        except (RuntimeError, ValueError, TypeError) as error:
            self._result = None
            self._graphs = []
            self.graph = None
            label = Gtk.Label(label=f"Flowchart unavailable: {error}")
            label.set_wrap(True)
            label.set_halign(Gtk.Align.START)
            self.scroller.set_child(label)
            return

        self._result = result
        self._graphs = graphs
        self._file_label.set_text(file_path.name if file_path else "Untitled source")
        names = [graph.function_name or "Program" for graph in graphs]
        self.function_selector.set_model(Gtk.StringList.new(names))
        self.function_selector.set_visible(len(graphs) > 1)
        selected = next(
            (index for index, graph in enumerate(graphs) if graph.function_name == "main"),
            0,
        )
        self.function_selector.set_selected(selected)
        self._set_graph(selected)

    def _set_graph(self, index: int) -> None:
        if not 0 <= index < len(self._graphs):
            return
        self.graph = self._graphs[index]
        self._selected_node_id = None
        self._render_graph()

    def _render_graph(self) -> None:
        if self.graph is None or not self.graph.nodes:
            self.scroller.set_child(self._empty_label)
            return

        max_y = max(node.y + node.height for node in self.graph.nodes)
        min_x = min(node.x for node in self.graph.nodes)
        max_x = max(node.x + node.width for node in self.graph.nodes)
        viewport_width = max(320, self.scroller.get_width())
        viewport_height = max(320, self.scroller.get_height())
        scale = self._graph_transform(self.graph, viewport_width)[0]
        self.canvas.set_content_width(
            max(viewport_width, math.ceil((max_x - min_x + 140) * scale * self._zoom))
        )
        self.canvas.set_content_height(
            max(viewport_height, math.ceil((max_y + 40) * scale * self._zoom))
        )
        self.scroller.set_child(self.canvas)
        self.canvas.queue_draw()

    def _on_function_selected(
        self, dropdown: Gtk.DropDown, _pspec: object
    ) -> None:
        self._set_graph(dropdown.get_selected())

    def _on_refresh_clicked(self, _button: Gtk.Button) -> None:
        self.set_source(self._source, self._file_path, self._language)

    def _change_zoom(self, factor: float) -> None:
        self._zoom = min(3.0, max(0.4, self._zoom * factor))
        self._render_graph()

    def _fit_graph(self, _button: Gtk.Button) -> None:
        self._zoom = 1.0
        self._render_graph()
        self.scroller.get_hadjustment().set_value(0)
        self.scroller.get_vadjustment().set_value(0)

    def _on_pan_begin(
        self, _gesture: Gtk.GestureDrag, _x: float, _y: float
    ) -> None:
        self._drag_origin = (
            self.scroller.get_hadjustment().get_value(),
            self.scroller.get_vadjustment().get_value(),
        )

    def _on_pan_update(
        self, _gesture: Gtk.GestureDrag, offset_x: float, offset_y: float
    ) -> None:
        horizontal = self.scroller.get_hadjustment()
        vertical = self.scroller.get_vadjustment()
        horizontal.set_value(
            min(horizontal.get_upper() - horizontal.get_page_size(),
                max(0, self._drag_origin[0] - offset_x))
        )
        vertical.set_value(
            min(vertical.get_upper() - vertical.get_page_size(),
                max(0, self._drag_origin[1] - offset_y))
        )

    def _on_export_clicked(self, _button: Gtk.Button, file_type: str) -> None:
        self.export_button.get_popover().popdown()
        root = self.get_root()
        if self.graph is None or not isinstance(root, Gtk.Window):
            return
        dialog = Gtk.FileChooserNative.new(
            f"Export Flowchart as {file_type.upper()}",
            root,
            Gtk.FileChooserAction.SAVE,
            "_Save",
            "_Cancel",
        )
        name = self.graph.function_name or "flowchart"
        dialog.set_current_name(f"{name}.{file_type}")
        dialog.connect("response", self._on_export_response, file_type)
        self._export_dialog = dialog
        dialog.show()

    def _on_export_response(
        self,
        dialog: Gtk.FileChooserNative,
        response: int,
        file_type: str,
    ) -> None:
        if response == Gtk.ResponseType.ACCEPT:
            selected = dialog.get_file()
            path = selected.get_path() if selected is not None else None
            if path is not None and self.graph is not None:
                try:
                    export = getattr(self._exporter, f"export_{file_type}")
                    export(self.graph, path)
                    self._status_label.set_text(f"Exported {Path(path).name}")
                except (OSError, RuntimeError, ValueError) as error:
                    self._status_label.set_text(f"Export failed: {error}")
        dialog.destroy()
        self._export_dialog = None

    def _on_canvas_pressed(
        self,
        _gesture: Gtk.GestureClick,
        _press_count: int,
        x: float,
        y: float,
    ) -> None:
        graph = self.graph
        if graph is None:
            return
        viewport_width = self.scroller.get_width() or self.canvas.get_width()
        scale, origin_x = self._graph_transform(graph, max(1, viewport_width))
        scale *= self._zoom
        graph_x = (x - origin_x * self._zoom) / scale
        graph_y = (y - 16 * self._zoom) / scale
        selected = next(
            (
                node
                for node in reversed(graph.nodes)
                if node.x <= graph_x <= node.x + node.width
                and node.y <= graph_y <= node.y + node.height
            ),
            None,
        )
        self._selected_node_id = selected.node_id if selected else None
        self.canvas.queue_draw()
        if (
            selected is None
            or selected.kind in {
                FlowchartNodeKind.START,
                FlowchartNodeKind.END,
                FlowchartNodeKind.MERGE,
                FlowchartNodeKind.CONNECTOR,
            }
            or self._result is None
            or self._on_source_navigate is None
        ):
            return
        ast_type = selected.metadata.get("ast_type")
        source_node = next(
            (
                node
                for node in self._result.root.walk()
                if node.node_type == ast_type
                and node.location.start_line == selected.line
                and node.location.start_column == selected.column
            ),
            None,
        )
        if source_node is not None:
            self._on_source_navigate(source_node)

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
        viewport_width = self.scroller.get_width() or width
        scale, origin_x = self._graph_transform(graph, viewport_width)
        context.translate(origin_x * self._zoom, 16 * self._zoom)
        scale *= self._zoom
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
        if node.node_id == self._selected_node_id:
            context.set_source_rgba(1.0, 0.88, 0.28, 1.0)
            context.set_line_width(3.2)
        else:
            context.set_source_rgba(*color, 1.0)
            context.set_line_width(2.0)
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
