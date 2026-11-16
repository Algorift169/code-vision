from __future__ import annotations

import math
from collections.abc import Callable
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from ...analysis.variable_flow import VariableFlowAnalysis
from ...graphs.variable_flow_builder import VariableFlowBuilder
from ...model import ASTNode
from ...parser import SourceParser


class VariableFlowView(Gtk.Box):
    """Interactive variable-flow workspace with explorer, canvas, and inspector."""

    def __init__(self, on_source_navigate: Callable[[ASTNode], None] | None = None) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_hexpand(True)
        self.set_vexpand(True)
        self._parser = SourceParser()
        self._builder = VariableFlowBuilder()
        self._analysis = VariableFlowAnalysis(source_file=None, language="unknown")
        self._on_source_navigate = on_source_navigate
        self._source: str | None = None
        self._file_path: Path | None = None
        self._language: str | None = None
        self._zoom = 1.0
        self._selected_fact = None
        self._selected_node_id: str | None = None
        self._graph = None

        self.title = Gtk.Label(label="Var Flow")
        self.title.set_halign(Gtk.Align.START)
        self.title.add_css_class("analysis-placeholder-title")
        self.title.set_hexpand(True)
        self.append(self.title)

        self.add_css_class("var-flow-panel")

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        header.set_hexpand(True)
        header.add_css_class("var-flow-header")
        self.header_title = Gtk.Label(label="Variable Flow")
        self.header_title.set_halign(Gtk.Align.START)
        self.header_title.set_hexpand(True)
        header.append(self.header_title)

        self.file_label = Gtk.Label(label="No source")
        self.file_label.set_ellipsize(3)
        header.append(self.file_label)

        self.refresh_button = Gtk.Button.new_from_icon_name("view-refresh-symbolic")
        self.refresh_button.add_css_class("var-flow-toolbar-button")
        self.refresh_button.set_tooltip_text("Refresh analysis")
        self.refresh_button.connect("clicked", self._on_refresh_clicked)
        header.append(self.refresh_button)

        self.fit_button = Gtk.Button.new_from_icon_name("zoom-fit-best-symbolic")
        self.fit_button.add_css_class("var-flow-toolbar-button")
        self.fit_button.set_tooltip_text("Fit graph")
        self.fit_button.connect("clicked", self._fit_graph)
        header.append(self.fit_button)

        self.reset_button = Gtk.Button.new_from_icon_name("edit-clear-symbolic")
        self.reset_button.add_css_class("var-flow-toolbar-button")
        self.reset_button.set_tooltip_text("Reset view")
        self.reset_button.connect("clicked", self._reset_view)
        header.append(self.reset_button)

        self.status_label = Gtk.Label(label="Ready")
        self.status_label.set_halign(Gtk.Align.END)
        header.append(self.status_label)
        self.append(header)

        self.summary_label = Gtk.Label(label="0 variables · 0 definitions · 0 uses")
        self.summary_label.set_halign(Gtk.Align.START)
        self.summary_label.add_css_class("var-flow-summary")
        self.append(self.summary_label)

        self.workspace = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.workspace.set_hexpand(True)
        self.workspace.set_vexpand(True)
        self.workspace.add_css_class("var-flow-workspace")

        self.explorer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.explorer.set_size_request(260, -1)
        self.explorer.add_css_class("var-flow-explorer")
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.add_css_class("var-flow-search-entry")
        self.search_entry.set_placeholder_text("Search variables...")
        self.search_entry.connect("search-changed", self._apply_filter)
        self.explorer.append(self.search_entry)

        self.variable_list = Gtk.ListBox()
        self.variable_list.add_css_class("var-flow-variable-list")
        self.variable_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.variable_list.connect("row-activated", self._on_variable_row_activated)
        self.variable_list.set_hexpand(True)
        self.variable_list.set_vexpand(True)
        self.explorer.append(self.variable_list)

        self.content_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.content_panel.set_hexpand(True)
        self.content_panel.set_vexpand(True)
        self.content_panel.add_css_class("var-flow-content-panel")

        self.canvas = Gtk.DrawingArea()
        self.canvas.set_name("variable-flow-canvas")
        self.canvas.set_hexpand(True)
        self.canvas.set_vexpand(True)
        self.canvas.set_draw_func(self._draw_graph)
        click = Gtk.GestureClick.new()
        click.connect("pressed", self._on_canvas_pressed)
        self.canvas.add_controller(click)

        self.canvas_scroller = Gtk.ScrolledWindow()
        self.canvas_scroller.add_css_class("var-flow-canvas-panel")
        self.canvas_scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.canvas_scroller.set_hexpand(True)
        self.canvas_scroller.set_vexpand(True)
        self.canvas_scroller.set_child(self.canvas)

        self.inspector = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.inspector.set_size_request(260, -1)
        self.inspector.add_css_class("var-flow-inspector")
        self.inspector_label = Gtk.Label(label="Node Inspector\nNo node selected")
        self.inspector_label.add_css_class("var-flow-inspector-label")
        self.inspector_label.set_wrap(True)
        self.inspector_label.set_xalign(0.0)
        self.inspector_label.set_yalign(0.0)
        self.inspector.append(self.inspector_label)

        self.go_to_source_button = Gtk.Button(label="Go to Source")
        self.go_to_source_button.add_css_class("var-flow-action-button")
        self.go_to_source_button.set_sensitive(False)
        self.go_to_source_button.connect("clicked", self._navigate_to_selected_source)
        self.inspector.append(self.go_to_source_button)

        self.content_panel.append(self.inspector)
        self.content_panel.append(self.canvas_scroller)

        self.workspace.append(self.explorer)
        self.workspace.append(self.content_panel)
        self.append(self.workspace)

        self._empty_state = Gtk.Label(label="Open a source file to inspect variable flow.")
        self._empty_state.set_wrap(True)
        self._empty_state.set_halign(Gtk.Align.CENTER)
        self._empty_state.set_valign(Gtk.Align.CENTER)
        self._raw_message = self._empty_state

    def set_source(self, source: str | None, file_path: Path | None, language: str | None = None) -> None:
        self._source = source
        self._file_path = file_path
        self._language = language
        if source is None or not source.strip():
            self._analysis = VariableFlowAnalysis(source_file=file_path, language=language or "unknown")
            self._analysis.facts = []
            self._graph = None
            self._selected_fact = None
            self._selected_node_id = None
            self._update_summary()
            self._set_inspector_text("Node Inspector\nNo node selected")
            self._populate_variable_list([])
            self._show_empty_state("Open a source file to inspect variable flow.")
            self.status_label.set_text("Idle")
            self.header_title.set_text("Variable Flow")
            return

        try:
            result = self._parser.parse(source, language=language, file_path=file_path)
            self._analysis = VariableFlowAnalysis(source_file=file_path, language=result.language)
            self._analysis.analyze(result)
            self._populate_variable_list(self._analysis.facts)
            self._selected_fact = self._analysis.facts[0] if self._analysis.facts else None
            self._update_selected_graph()
            self.status_label.set_text("Analyzed")
            self.header_title.set_text(f"Variable Flow · {file_path.name if file_path else 'Untitled source'}")
            self.file_label.set_text(file_path.name if file_path else "Untitled source")
            self._update_summary()
        except (RuntimeError, ValueError, TypeError) as error:
            self._analysis = VariableFlowAnalysis(source_file=file_path, language=language or "unknown")
            self._analysis.facts = []
            self._graph = None
            self._selected_fact = None
            self._selected_node_id = None
            self._set_inspector_text(f"Node Inspector\nAnalysis unavailable\n{error}")
            self._populate_variable_list([])
            self._show_empty_state(f"Variable flow unavailable: {error}")
            self.status_label.set_text("Unavailable")
            self.header_title.set_text("Variable Flow")
            self.file_label.set_text(file_path.name if file_path else "No source")
            self._update_summary()

    def _on_refresh_clicked(self, _button: Gtk.Button) -> None:
        self.set_source(self._source, self._file_path, self._language)

    def _change_zoom(self, factor: float) -> None:
        self._zoom = min(3.0, max(0.5, self._zoom * factor))
        self._render_graph()

    def zoom_in(self) -> None:
        self._change_zoom(1.25)

    def zoom_out(self) -> None:
        self._change_zoom(0.8)

    def _fit_graph(self, _button: Gtk.Button) -> None:
        self._zoom = 1.0
        self._render_graph()

    def _reset_view(self, _button: Gtk.Button) -> None:
        self._zoom = 1.0
        self._selected_node_id = None
        self._render_graph()
        self._set_inspector_text("Node Inspector\nNo node selected")

    def _apply_filter(self, entry: Gtk.SearchEntry) -> None:
        query = (entry.get_text() or "").strip().lower()
        visible = []
        for fact in self._analysis.facts:
            if not query or query in fact.name.lower() or query in (fact.scope or "").lower():
                visible.append(fact)
        self._populate_variable_list(visible)
        if visible:
            self._selected_fact = visible[0]
            self._update_selected_graph()
        else:
            self._selected_fact = None
            self._graph = None
            self._selected_node_id = None
            self._set_inspector_text("Node Inspector\nNo matching variables")
            self._show_empty_state("No variables match the current search.")

    def _populate_variable_list(self, facts: list) -> None:
        child = self.variable_list.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            self.variable_list.remove(child)
            child = next_child
        if not facts:
            self._show_empty_state("No variables detected for this source.")
            return

        groups: dict[str, list] = {}
        for fact in facts:
            groups.setdefault(fact.scope, []).append(fact)

        first_data_row = None
        for scope_name in sorted(groups):
            label = Gtk.Label(label=f"{scope_name.upper()}" if scope_name else "MODULE")
            label.add_css_class("analysis-placeholder-title")
            label.set_halign(Gtk.Align.START)
            row = Gtk.ListBoxRow()
            row.set_selectable(False)
            row.set_child(label)
            self.variable_list.append(row)
            for fact in sorted(groups[scope_name], key=lambda item: item.name):
                item = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
                item.set_margin_start(8)
                item.set_margin_top(3)
                item.set_margin_bottom(3)
                name = Gtk.Label(label=fact.name)
                name.set_halign(Gtk.Align.START)
                name.set_xalign(0.0)
                detail = Gtk.Label(label=f"{len(fact.definitions)} definitions · {len(fact.uses)} uses")
                detail.set_halign(Gtk.Align.START)
                detail.set_xalign(0.0)
                item.append(name)
                item.append(detail)
                row_widget = Gtk.ListBoxRow()
                row_widget.set_child(item)
                row_widget.fact = fact
                self.variable_list.append(row_widget)
                if first_data_row is None:
                    first_data_row = row_widget

        if first_data_row is not None:
            self.variable_list.select_row(first_data_row)

    def _on_variable_row_activated(self, _list_box: Gtk.ListBox, row: Gtk.ListBoxRow) -> None:
        fact = getattr(row, "fact", None)
        if fact is None:
            return
        self._selected_fact = fact
        self._update_selected_graph()

    def _update_selected_graph(self) -> None:
        if self._selected_fact is None:
            self._graph = None
            self._selected_node_id = None
            self._set_inspector_text("Node Inspector\nNo variable selected")
            return
        if self._source is None or not self._source.strip():
            self._graph = None
            self._selected_node_id = None
            self._set_inspector_text("Node Inspector\nNo source available")
            return

        try:
            result = self._parser.parse(
                self._source,
                language=self._language,
                file_path=self._file_path,
            )
        except (RuntimeError, ValueError, TypeError) as error:
            self._graph = None
            self._selected_node_id = None
            self._set_inspector_text(f"Node Inspector\nAnalysis unavailable\n{error}")
            self.status_label.set_text("Unavailable")
            return

        graph = self._builder.build(result, self._selected_fact.name, scope=self._selected_fact.scope)
        self._graph = graph
        self._selected_node_id = graph.nodes[0].node_id if graph.nodes else None
        self._layout_graph(graph)
        self._render_graph()
        self._populate_inspector_from_selection()

    def _layout_graph(self, graph) -> None:
        if graph is None or not graph.nodes:
            return
        for index, node in enumerate(graph.nodes):
            node.x = 30 + (index % 2) * 240
            node.y = 30 + (index // 2) * 110
            node.width = 180
            node.height = 72

    def _render_graph(self) -> None:
        if self._graph is None or not self._graph.nodes:
            self.canvas.set_content_width(320)
            self.canvas.set_content_height(240)
            self.canvas.queue_draw()
            return
        width = max(320, math.ceil((max(node.x + node.width for node in self._graph.nodes) + 30) * self._zoom))
        height = max(240, math.ceil((max(node.y + node.height for node in self._graph.nodes) + 30) * self._zoom))
        self.canvas.set_content_width(width)
        self.canvas.set_content_height(height)
        self.canvas.queue_draw()

    def _draw_graph(self, _area: Gtk.DrawingArea, context, width: int, height: int) -> None:
        context.set_line_width(1.5)
        graph = self._graph
        if graph is None or not graph.nodes:
            return
        node_map = {node.node_id: node for node in graph.nodes}
        for edge in graph.edges:
            source = node_map.get(edge.source_id)
            target = node_map.get(edge.target_id)
            if source is None or target is None:
                continue
            start_x = source.x + source.width / 2
            start_y = source.y + source.height
            end_x = target.x + target.width / 2
            end_y = target.y
            mid_y = (start_y + end_y) / 2
            context.move_to(start_x * self._zoom, start_y * self._zoom)
            context.curve_to(
                start_x * self._zoom,
                mid_y * self._zoom,
                end_x * self._zoom,
                mid_y * self._zoom,
                end_x * self._zoom,
                end_y * self._zoom,
            )
            context.set_source_rgb(0.45, 0.63, 0.8)
            context.stroke()

        for node in graph.nodes:
            x = node.x * self._zoom
            y = node.y * self._zoom
            w = node.width * self._zoom
            h = node.height * self._zoom
            if node.node_id == self._selected_node_id:
                context.set_source_rgb(0.20, 0.66, 0.89)
            else:
                colors = {
                    "initialization": (0.22, 0.50, 0.78),
                    "assignment": (0.38, 0.68, 0.32),
                    "merge": (0.82, 0.52, 0.16),
                    "usage": (0.72, 0.32, 0.32),
                    "read": (0.72, 0.32, 0.32),
                    "definition": (0.32, 0.55, 0.75),
                    "return": (0.82, 0.30, 0.30),
                }
                context.set_source_rgb(*colors.get(node.kind, (0.35, 0.52, 0.72)))
            context.rectangle(x, y, w, h)
            context.fill_preserve()
            context.set_source_rgb(0.14, 0.15, 0.18)
            context.stroke()
            context.set_source_rgb(0.95, 0.96, 0.98)
            context.move_to(x + 10, y + 12)
            context.show_text(node.kind.upper())
            context.move_to(x + 10, y + 30)
            context.show_text(node.name)
            context.move_to(x + 10, y + 48)
            context.show_text((node.metadata.get("expression") or "").strip()[:26])
            context.move_to(x + 10, y + 58)
            context.show_text(f"Line {node.metadata.get('source_line', '?')}")

    def _on_canvas_pressed(self, _gesture: Gtk.GestureClick, _n_press: int, x: float, y: float) -> None:
        if self._graph is None:
            return
        x /= self._zoom
        y /= self._zoom
        node = next(
            (
                item for item in reversed(self._graph.nodes)
                if item.x <= x <= item.x + item.width and item.y <= y <= item.y + item.height
            ),
            None,
        )
        if node is None:
            return
        self._selected_node_id = node.node_id
        self._populate_inspector_from_selection()
        if self._on_source_navigate is not None and node.source_node is not None and node.source_node.location.has_range:
            if _n_press >= 2:
                self._on_source_navigate(node.source_node)

    def _populate_inspector_from_selection(self) -> None:
        if self._graph is None:
            self._set_inspector_text("Node Inspector\nNo graph available")
            self.go_to_source_button.set_sensitive(False)
            return
        node = next((item for item in self._graph.nodes if item.node_id == self._selected_node_id), None)
        if node is None:
            self._set_inspector_text("Node Inspector\nNo node selected")
            self.go_to_source_button.set_sensitive(False)
            return
        lines = [
            "NODE INSPECTOR",
            f"Type: {node.kind.title()}",
            f"Variable: {self._selected_fact.name if self._selected_fact else node.name}",
            f"Scope: {self._selected_fact.scope if self._selected_fact else node.scope}",
            f"Expression: {node.metadata.get('expression', '')}",
            f"Source: {self._file_path.name if self._file_path else 'Untitled source'}",
            f"Line: {node.metadata.get('source_line', '?')}",
        ]
        self._set_inspector_text("\n".join(lines))
        self.go_to_source_button.set_sensitive(node.source_node is not None and node.source_node.location.has_range and self._on_source_navigate is not None)

    def _set_inspector_text(self, text: str) -> None:
        self.inspector_label.set_text(text)

    def _navigate_to_selected_source(self, _button: Gtk.Button) -> None:
        if self._graph is None or self._selected_node_id is None or self._on_source_navigate is None:
            return
        node = next((item for item in self._graph.nodes if item.node_id == self._selected_node_id), None)
        if node is not None and node.source_node is not None and node.source_node.location.has_range:
            self._on_source_navigate(node.source_node)

    def _show_empty_state(self, message: str) -> None:
        self._empty_state.set_text(message)
        if self.variable_list.get_first_child() is not None:
            return
        self.canvas_scroller.set_child(self._empty_state)

    def _update_summary(self) -> None:
        definitions = sum(len(fact.definitions) for fact in self._analysis.facts)
        uses = sum(len(fact.uses) for fact in self._analysis.facts)
        self.summary_label.set_text(f"{len(self._analysis.facts)} variables · {definitions} definitions · {uses} uses")


__all__ = ["VariableFlowView"]
