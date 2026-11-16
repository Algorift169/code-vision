from __future__ import annotations

from datetime import datetime
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from ..complexity import ComplexityAnalyzer
from ..model.ast_node import ASTNode
from ..model.source_location import SourceLocation


class ComplexityView(Gtk.Box):
    """Professional static complexity dashboard for the Analysis Panel."""

    _RISK_ORDER = {"low": 0, "moderate": 1, "high": 2}
    _CLASSIFICATION_ORDER = {"low": 0, "moderate": 1, "high": 2, "very high": 3}

    def __init__(self, on_source_navigate=None) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_name("complexity-view")
        self.set_hexpand(True)
        self.set_vexpand(True)
        self._on_source_navigate = on_source_navigate
        self._zoom_level = 0
        self._zoom_provider: Gtk.CssProvider | None = None
        self._source: str | None = None
        self._file_path: Path | None = None
        self._language: str | None = None
        self._report = None
        self._selected_function = None
        self._filtered_functions: list = []
        self._search_text = ""
        self._risk_filter = "all"
        self._category_filter = "all"
        self._sort_key = "cyclomatic"
        self._sort_desc = True
        self._last_analyzed = datetime.now()

        self.section_title = Gtk.Label(label="Complexity")
        self.section_title.add_css_class("analysis-placeholder-title")
        self.section_title.set_halign(Gtk.Align.START)
        self.append(self.section_title)

        self.header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.header.set_hexpand(True)
        self.header.add_css_class("complexity-header")

        self.title = Gtk.Label(label="Complexity Analysis")
        self.title.add_css_class("complexity-header-title")
        self.title.set_hexpand(True)
        self.title.set_halign(Gtk.Align.START)
        self.header.append(self.title)

        self.status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.status_box.add_css_class("complexity-status-box")
        self.file_label = Gtk.Label(label="No file selected")
        self.file_label.add_css_class("complexity-meta-label")
        self.status_box.append(self.file_label)
        self.status_badge = Gtk.Label(label="Ready")
        self.status_badge.add_css_class("complexity-status-badge")
        self.status_box.append(self.status_badge)
        self.refresh_button = Gtk.Button(label="Reanalyze")
        self.refresh_button.add_css_class("theme-toolbar-button")
        self.refresh_button.connect("clicked", self._on_refresh_clicked)
        self.header.append(self.status_box)
        self.header.append(self.refresh_button)
        self.append(self.header)

        self.summary = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.summary.set_hexpand(True)
        self.summary.add_css_class("complexity-summary-grid")
        self.append(self.summary)

        self.distribution_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.distribution_box.set_hexpand(True)
        self.distribution_box.add_css_class("complexity-distribution-box")
        self.append(self.distribution_box)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.main_box.set_hexpand(True)
        self.main_box.set_vexpand(True)
        self.main_box.add_css_class("complexity-main-box")

        self.table_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.table_panel.set_hexpand(True)
        self.table_panel.set_vexpand(True)

        self.table_filters = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.table_filters.set_hexpand(True)
        self.table_filters.add_css_class("complexity-table-toolbar")

        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search functions...")
        self.search_entry.connect("search-changed", self._on_search_changed)
        self.table_filters.append(self.search_entry)

        self.filter_buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.filter_buttons.set_hexpand(True)
        self.filter_buttons.add_css_class("complexity-filter-buttons")
        self.table_filters.append(self.filter_buttons)
        self.table_panel.append(self.table_filters)

        self.list_box = Gtk.ListBox()
        self.list_box.add_css_class("complexity-function-list")
        self.list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.list_box.set_hexpand(True)
        self.list_box.set_vexpand(True)
        self.list_box.connect("row-selected", self._on_table_row_selected)
        self.table_scroll = Gtk.ScrolledWindow()
        self.table_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.table_scroll.set_hexpand(True)
        self.table_scroll.set_vexpand(True)
        self.table_scroll.set_child(self.list_box)
        self.table_panel.append(self.table_scroll)

        self.details_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.details_panel.set_size_request(300, -1)
        self.details_panel.add_css_class("complexity-details-panel")
        self.details_title = Gtk.Label(label="Selected Function")
        self.details_title.add_css_class("complexity-panel-title")
        self.details_panel.append(self.details_title)
        self.details_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.details_content.set_hexpand(True)
        self.details_panel.append(self.details_content)
        self.main_box.append(self.table_panel)
        self.main_box.append(self.details_panel)
        self.append(self.main_box)

        self.hotspots_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.hotspots_box.add_css_class("complexity-hotspots")
        self.hotspots_title = Gtk.Label(label="Complexity Hotspots")
        self.hotspots_title.add_css_class("complexity-panel-title")
        self.hotspots_box.append(self.hotspots_title)
        self.hotspot_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.hotspot_list.add_css_class("complexity-hotspot-list")
        self.hotspots_box.append(self.hotspot_list)
        self.append(self.hotspots_box)

        self.empty_state = Gtk.Label(label="Open a source file to inspect complexity.")
        self.empty_state.set_wrap(True)
        self.empty_state.set_halign(Gtk.Align.CENTER)
        self.empty_state.set_valign(Gtk.Align.CENTER)
        self.empty_state.add_css_class("analysis-placeholder-title")

        self._render_empty_state()

    def set_source(self, source: str | None, file_path: Path | None, language: str | None = None) -> None:
        self._source = source
        self._file_path = file_path
        self._language = language
        self._last_analyzed = datetime.now()
        self.file_label.set_text(file_path.name if file_path else "No file selected")

        if source is None or not source.strip():
            self._report = None
            self._selected_function = None
            self._filtered_functions = []
            self._render_empty_state()
            return

        try:
            self._report = ComplexityAnalyzer().analyze(source, file_path=file_path, language=language)
        except Exception as error:  # pragma: no cover - UI safety fallback
            self._report = None
            self._selected_function = None
            self._filtered_functions = []
            self._render_error_state(str(error))
            return

        self.status_badge.set_text("Analyzed")
        self._apply_filters()

    def _on_refresh_clicked(self, _button: Gtk.Button) -> None:
        self.set_source(self._source, self._file_path, self._language)

    def zoom_in(self) -> None:
        self._zoom_level = min(self._zoom_level + 1, 5)
        self._apply_local_zoom()

    def zoom_out(self) -> None:
        self._zoom_level = max(self._zoom_level - 1, -3)
        self._apply_local_zoom()

    def _apply_local_zoom(self) -> None:
        if self._zoom_provider is None:
            self._zoom_provider = Gtk.CssProvider()
            Gtk.StyleContext.add_provider_for_display(
                self.get_display(),
                self._zoom_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_USER,
            )

        font_size = max(9, 12 + self._zoom_level)
        self._zoom_provider.load_from_string(
            f"#analysis-panel #complexity-view * {{ font-size: {font_size}px; }}"
        )

    def _render_empty_state(self) -> None:
        self._clear_summary_cards()
        self._clear_distribution()
        self._clear_table(); self._clear_details(); self._clear_hotspots()
        self.summary.append(self.empty_state)
        self.hotspots_box.set_visible(False)

    def _render_error_state(self, error: str) -> None:
        self._clear_summary_cards(); self._clear_distribution(); self._clear_table(); self._clear_details(); self._clear_hotspots()
        self.summary.append(Gtk.Label(label=f"Complexity unavailable: {error}"))
        self.hotspots_box.set_visible(False)

    def _clear_summary_cards(self) -> None:
        for child in list(self.summary):
            self.summary.remove(child)

    def _clear_distribution(self) -> None:
        for child in list(self.distribution_box):
            self.distribution_box.remove(child)

    def _clear_table(self) -> None:
        for child in list(self.list_box):
            self.list_box.remove(child)

    def _clear_details(self) -> None:
        for child in list(self.details_content):
            self.details_content.remove(child)

    def _clear_hotspots(self) -> None:
        for child in list(self.hotspot_list):
            self.hotspot_list.remove(child)

    def _apply_filters(self) -> None:
        if self._report is None:
            self._render_empty_state()
            return

        functions = list(self._report.functions)
        query = self._search_text.strip().lower()
        if query:
            functions = [item for item in functions if query in item.name.lower()]
        if self._risk_filter != "all":
            functions = [item for item in functions if item.risk.lower() == self._risk_filter]
        if self._category_filter != "all":
            functions = [
                item for item in functions if self._classify_metric(item.cyclomatic).lower() == self._category_filter.lower()
            ]

        sort_key = self._sort_key
        if sort_key == "risk":
            functions = sorted(functions, key=lambda item: self._RISK_ORDER.get(item.risk.lower(), -1), reverse=self._sort_desc)
        elif sort_key == "name":
            functions = sorted(functions, key=lambda item: item.name.lower(), reverse=self._sort_desc)
        elif sort_key == "location":
            functions = sorted(functions, key=lambda item: item.line, reverse=self._sort_desc)
        else:
            functions = sorted(functions, key=lambda item: getattr(item, sort_key, 0) or 0, reverse=self._sort_desc)

        self._filtered_functions = functions
        self._selected_function = self._filtered_functions[0] if self._filtered_functions else None
        self._render_summary_cards(self._report)
        self._render_distribution(self._report.functions)
        self._render_function_table(self._filtered_functions)
        self._render_details(self._selected_function)
        self._render_hotspots(self._report.hotspots)
        self.hotspots_box.set_visible(True)
        self._render_filter_buttons()

    def _render_filter_buttons(self) -> None:
        for child in list(self.filter_buttons):
            self.filter_buttons.remove(child)

        for label in ["All", "Low", "Moderate", "High", "Very High"]:
            button = Gtk.ToggleButton(label=label)
            button.add_css_class("complexity-filter-button")
            active = label.lower() == self._category_filter.lower() or (label == "All" and self._category_filter == "all")
            button.set_active(active)
            button.connect("toggled", self._on_category_filter_toggled, label)
            self.filter_buttons.append(button)

    def _on_category_filter_toggled(self, button: Gtk.ToggleButton, label: str) -> None:
        if not button.get_active():
            return
        self._category_filter = "all" if label == "All" else label
        self._apply_filters()

    def _on_search_changed(self, entry: Gtk.SearchEntry) -> None:
        self._search_text = entry.get_text() or ""
        self._apply_filters()

    def _render_summary_cards(self, report) -> None:
        self._clear_summary_cards()
        if report is None or not report.functions:
            self.summary.append(self.empty_state)
            return

        total_functions = len(report.functions)
        average_cyclomatic = report.average_cyclomatic
        average_cognitive = report.average_cognitive
        high_risk = sum(1 for fn in report.functions if fn.risk in {"high"})
        highest = report.highest_complexity
        if highest is None:
            highest_name = "N/A"
            highest_value = "N/A"
        else:
            highest_name = highest.name
            highest_value = str(highest.cyclomatic)

        cards = [
            ("Total Functions", str(total_functions), "Functions analyzed", "low"),
            ("Average Cyclomatic", f"{average_cyclomatic:.1f}", self._classify_metric(average_cyclomatic), "low"),
            ("Average Cognitive", f"{average_cognitive:.1f}", self._classify_metric(average_cognitive, "cognitive"), "moderate"),
            ("High Complexity", f"{high_risk}", f"{(high_risk / total_functions * 100):.0f}% of functions", "high"),
            ("Highest Complexity", highest_name, f"{highest_value} cyclomatic", "high"),
        ]

        for title, value, subtitle, tone in cards:
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            card.set_hexpand(True)
            card.add_css_class("complexity-metric-card")
            card.add_css_class(f"complexity-card-{tone}")
            title_label = Gtk.Label(label=title)
            title_label.add_css_class("complexity-card-title")
            value_label = Gtk.Label(label=value)
            value_label.add_css_class("complexity-card-value")
            subtitle_label = Gtk.Label(label=subtitle)
            subtitle_label.add_css_class("complexity-card-subtitle")
            progress = Gtk.ProgressBar()
            progress.set_fraction(0.5 if tone == "low" else 0.7 if tone == "moderate" else 0.9)
            progress.add_css_class(f"complexity-progress-{tone}")
            card.append(title_label)
            card.append(value_label)
            card.append(subtitle_label)
            card.append(progress)
            self.summary.append(card)

    def _classify_metric(self, value: float, kind: str = "cyclomatic") -> str:
        if kind == "cognitive":
            if value >= 16:
                return "Very High"
            if value >= 8:
                return "High"
            if value >= 4:
                return "Moderate"
            return "Low"
        if value >= 15:
            return "Very High"
        if value >= 8:
            return "High"
        if value >= 4:
            return "Moderate"
        return "Low"

    def _render_distribution(self, functions) -> None:
        self._clear_distribution()
        if not functions:
            state = Gtk.Label(label="No complexity distribution data available.")
            state.add_css_class("complexity-empty-label")
            self.distribution_box.append(state)
            return

        for name, metric_name in (("Cyclomatic Complexity Distribution", "cyclomatic"), ("Cognitive Complexity Distribution", "cognitive")):
            panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            panel.set_hexpand(True)
            panel.add_css_class("complexity-chart-panel")
            title = Gtk.Label(label=name)
            title.add_css_class("complexity-panel-title")
            panel.append(title)
            counts = {"Low": 0, "Moderate": 0, "High": 0, "Very High": 0}
            for item in functions:
                value = getattr(item, metric_name, 0)
                counts[self._classify_metric(value, metric_name)] += 1

            total = sum(counts.values()) or 1
            for label_name, count in counts.items():
                row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
                row.set_hexpand(True)
                row.add_css_class("complexity-chart-row")
                button = Gtk.Button(label=f"{label_name}")
                button.add_css_class("complexity-chart-button")
                button.set_tooltip_text(f"{count} functions ({(count / total) * 100:.0f}%)")
                button.connect("clicked", self._on_distribution_clicked, label_name)
                bar = Gtk.ProgressBar()
                bar.set_fraction(count / total if total else 0)
                bar.add_css_class(f"complexity-bar-{label_name.lower().replace(' ', '-')}")
                value_label = Gtk.Label(label=str(count))
                value_label.add_css_class("complexity-chart-count")
                row.append(button)
                row.append(bar)
                row.append(value_label)
                panel.append(row)
            self.distribution_box.append(panel)

    def _on_distribution_clicked(self, button: Gtk.Button, category: str) -> None:
        self._category_filter = category
        self._apply_filters()

    def _render_function_table(self, functions) -> None:
        self._clear_table()
        if not functions:
            row = Gtk.ListBoxRow()
            label = Gtk.Label(label="No functions match the selected filters.")
            label.add_css_class("complexity-empty-label")
            row.set_child(label)
            self.list_box.append(row)
            return

        for item in functions:
            row = Gtk.ListBoxRow()
            row.set_selectable(True)
            row.set_activatable(True)
            row.set_name(f"complexity-row-{item.name}")
            row._complexity_item = item
            row.connect("activate", self._on_function_activate, item)

            content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            content.set_hexpand(True)
            content.add_css_class("complexity-function-row")

            name_label = Gtk.Label(label=item.name)
            name_label.set_xalign(0)
            name_label.set_hexpand(True)
            location_label = Gtk.Label(label=f"{self._file_path.name if self._file_path else 'source'}:{item.line}")
            cyclo_label = Gtk.Label(label=str(item.cyclomatic))
            cognitive_label = Gtk.Label(label=str(item.cognitive))
            time_label = Gtk.Label(label=item.time_complexity)
            space_label = Gtk.Label(label=item.space_complexity)
            maintain_label = Gtk.Label(label=f"{item.maintainability:.1f}" if item.maintainability is not None else "N/A")
            risk_label = Gtk.Label(label=item.risk.title())
            risk_label.add_css_class(f"complexity-risk-{item.risk.lower()}")

            for label in (name_label, location_label, cyclo_label, cognitive_label, time_label, space_label, maintain_label, risk_label):
                label.set_xalign(0)
                label.set_yalign(0.5)
            content.append(name_label)
            content.append(location_label)
            content.append(cyclo_label)
            content.append(cognitive_label)
            content.append(time_label)
            content.append(space_label)
            content.append(maintain_label)
            content.append(risk_label)
            row.set_child(content)
            self.list_box.append(row)

    def _on_function_activate(self, row: Gtk.ListBoxRow, item) -> None:
        self._selected_function = item
        self._render_details(item)
        if self._on_source_navigate is not None:
            node = ASTNode(
                node_id=f"complexity-{item.name}-{item.line}",
                node_type="function_definition",
                display_name=item.name,
                source_text=item.name,
                location=SourceLocation(item.line, 1, item.line, 1, 0, 0),
            )
            self._on_source_navigate(node)

    def _on_table_row_selected(self, list_box: Gtk.ListBox, row: Gtk.ListBoxRow | None) -> None:
        if row is None:
            return
        item = getattr(row, "_complexity_item", None)
        if item is not None:
            self._selected_function = item
            self._render_details(item)

    def _render_details(self, item) -> None:
        self._clear_details()
        if item is None:
            empty = Gtk.Label(label="Select a function to inspect its complexity details.")
            empty.add_css_class("complexity-empty-label")
            self.details_content.append(empty)
            return

        self.details_title.set_text(item.name)
        summary = Gtk.Label(label=f"Source: {self._file_path.name if self._file_path else 'Unknown'}:{item.line}\nRisk: {item.risk.title()}\nTime: {item.time_complexity} | Space: {item.space_complexity}")
        summary.set_wrap(True)
        summary.add_css_class("complexity-details-summary")
        self.details_content.append(summary)

        metric_rows = [
            ("Cyclomatic", str(item.cyclomatic)),
            ("Cognitive", str(item.cognitive)),
            ("Maintainability", f"{item.maintainability:.1f}" if item.maintainability is not None else "Unknown"),
            ("Risk", item.risk.title()),
        ]
        for label_text, value_text in metric_rows:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            row.set_hexpand(True)
            title = Gtk.Label(label=f"{label_text}:")
            value = Gtk.Label(label=value_text)
            value.set_halign(Gtk.Align.END)
            value.set_hexpand(True)
            row.append(title)
            row.append(value)
            self.details_content.append(row)

        explanation = Gtk.Label(label=item.explanation or "No additional explanation available.")
        explanation.set_wrap(True)
        explanation.add_css_class("complexity-details-copy")
        self.details_content.append(explanation)

        evidence = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        evidence.add_css_class("complexity-evidence-panel")
        evidence_label = Gtk.Label(label="Evidence")
        evidence_label.add_css_class("complexity-panel-subtitle")
        evidence.append(evidence_label)
        for note in item.evidence or ["No evidence recorded for this function."]:
            note_label = Gtk.Label(label=f"• {note}")
            note_label.set_wrap(True)
            evidence.append(note_label)
        self.details_content.append(evidence)

    def _render_hotspots(self, hotspots) -> None:
        self._clear_hotspots()
        if not hotspots:
            empty = Gtk.Label(label="No hotspots detected.")
            empty.add_css_class("complexity-empty-label")
            self.hotspot_list.append(empty)
            return

        for item in hotspots[:5]:
            hotspot = Gtk.Button()
            hotspot.set_hexpand(True)
            hotspot.add_css_class("complexity-hotspot-item")
            hotspot_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            hotspot_box.set_hexpand(True)
            info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            title = Gtk.Label(label=item.name)
            title.add_css_class("complexity-hotspot-title")
            location = Gtk.Label(label=f"{self._file_path.name if self._file_path else 'source'}:{item.line}")
            location.add_css_class("complexity-hotspot-meta")
            info.append(title)
            info.append(location)
            badge = Gtk.Label(label=item.risk.title())
            badge.add_css_class(f"complexity-risk-{item.risk.lower()}")
            hotspot_box.append(info)
            hotspot_box.append(badge)
            hotspot.set_child(hotspot_box)
            hotspot.connect("clicked", self._on_hotspot_click, item)
            self.hotspot_list.append(hotspot)

    def _on_hotspot_click(self, widget: Gtk.Button, item) -> None:
        self._selected_function = item
        self._render_details(item)
        if self._on_source_navigate is not None:
            node = ASTNode(
                node_id=f"hotspot-{item.name}-{item.line}",
                node_type="function_definition",
                display_name=item.name,
                source_text=item.name,
                location=SourceLocation(item.line, 1, item.line, 1, 0, 0),
            )
            self._on_source_navigate(node)


__all__ = ["ComplexityView"]
