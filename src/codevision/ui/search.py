"""VS Code-style workspace search dropdown for the main window."""

from __future__ import annotations

from pathlib import Path

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, GLib, Gtk

from ..services.file_search import FileSearchService, SearchResult, SearchResults


class WorkspaceSearch:
    """Connect a SearchEntry to an asynchronous, keyboard-navigable result list."""

    def __init__(
        self,
        entry: Gtk.SearchEntry,
        root_provider,
        on_file_open,
        on_folder_reveal,
    ) -> None:
        self.entry = entry
        self._root_provider = root_provider
        self._on_file_open = on_file_open
        self._on_folder_reveal = on_folder_reveal
        self._service = FileSearchService()
        self._generation = 0
        self._debounce_source = 0
        self._rows: list[Gtk.ListBoxRow] = []
        self._results: dict[Gtk.ListBoxRow, SearchResult] = {}

        self.results_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.results_panel.set_size_request(560, -1)
        self.results_panel.set_halign(Gtk.Align.CENTER)
        self.results_panel.set_valign(Gtk.Align.START)
        self.results_panel.set_visible(False)
        self.results_panel.add_css_class("search-popover")

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        content.set_margin_top(8)
        content.set_margin_bottom(8)
        content.set_margin_start(8)
        content.set_margin_end(8)
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_max_content_height(360)
        scrolled.set_propagate_natural_height(True)
        self.list_box = Gtk.ListBox()
        self.list_box.add_css_class("search-result-list")
        self.list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.list_box.connect("row-activated", self._on_row_activated)
        scrolled.set_child(self.list_box)
        content.append(scrolled)
        self.status = Gtk.Label(label="Start typing to search files and folders")
        self.status.add_css_class("search-result-status")
        self.status.set_xalign(0)
        content.append(self.status)
        self.results_panel.append(content)

        entry.connect("search-changed", self._on_search_changed)
        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", self._on_key_pressed)
        entry.add_controller(keys)

    def close(self) -> None:
        self._generation += 1
        if self._debounce_source:
            GLib.source_remove(self._debounce_source)
            self._debounce_source = 0
        self._service.shutdown()
        self.results_panel.set_visible(False)

    def _on_search_changed(self, _entry: Gtk.SearchEntry) -> None:
        query = self.entry.get_text().strip()
        self._generation += 1
        generation = self._generation
        if self._debounce_source:
            GLib.source_remove(self._debounce_source)
            self._debounce_source = 0
        if not query:
            self.results_panel.set_visible(False)
            self._clear_results("Start typing to search files and folders")
            return
        self._clear_results("Searching…")
        self.results_panel.set_visible(True)
        self._debounce_source = GLib.timeout_add(120, self._start_search, generation, query)

    def _start_search(self, generation: int, query: str) -> bool:
        self._debounce_source = 0
        root = self._root_provider()
        if root is None:
            self._clear_results("Open a project folder to search")
            return GLib.SOURCE_REMOVE
        future = self._service.submit(root, query)
        GLib.timeout_add(16, self._poll_search, generation, future)
        return GLib.SOURCE_REMOVE

    def _poll_search(self, generation: int, future) -> bool:
        if generation != self._generation:
            return GLib.SOURCE_REMOVE
        if not future.done():
            return GLib.SOURCE_CONTINUE
        try:
            results = future.result()
        except (OSError, RuntimeError, ValueError) as error:
            self._display_error(generation, str(error))
        else:
            self._display_results(generation, results)
        return GLib.SOURCE_REMOVE

    def _display_results(self, generation: int, results: SearchResults) -> bool:
        if generation != self._generation:
            return GLib.SOURCE_REMOVE
        self._clear_rows()
        for result in results.entries:
            row = self._create_row(result)
            self._rows.append(row)
            self._results[row] = result
            self.list_box.append(row)
        if results.total_count == 0:
            self.status.set_text("No matching files or folders")
        elif results.total_count > len(results.entries):
            self.status.set_text(f"Showing {len(results.entries)} of {results.total_count} results")
        else:
            self.status.set_text(f"{results.total_count} result{'s' if results.total_count != 1 else ''}")
        if self._rows:
            self.list_box.select_row(self._rows[0])
        return GLib.SOURCE_REMOVE

    def _display_error(self, generation: int, message: str) -> bool:
        if generation == self._generation:
            self._clear_results(f"Search failed: {message}")
        return GLib.SOURCE_REMOVE

    def _create_row(self, result: SearchResult) -> Gtk.ListBoxRow:
        row = Gtk.ListBoxRow()
        row.add_css_class("search-result")
        if result.is_hidden:
            row.add_css_class("search-result-hidden")
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.set_margin_top(5)
        box.set_margin_bottom(5)
        box.set_margin_start(6)
        box.set_margin_end(6)
        icon = Gtk.Image.new_from_icon_name(
            "folder-symbolic" if result.is_directory else "text-x-generic-symbolic"
        )
        icon.set_valign(Gtk.Align.CENTER)
        box.append(icon)
        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        name = Gtk.Label()
        name.set_markup(_highlight(result.name, result.match_indices))
        name.set_use_markup(True)
        name.set_xalign(0)
        name.set_ellipsize(3)
        name.add_css_class("search-result-name")
        path = result.relative_path.parent.as_posix() or "./"
        path_label = Gtk.Label(label=path)
        path_label.set_xalign(0)
        path_label.set_ellipsize(3)
        path_label.add_css_class("search-result-path")
        text.append(name)
        text.append(path_label)
        box.append(text)
        row.set_child(box)
        return row

    def _on_row_activated(self, _list: Gtk.ListBox, row: Gtk.ListBoxRow) -> None:
        result = self._results.get(row)
        if result is None:
            return
        self.results_panel.set_visible(False)
        if result.is_directory:
            self._on_folder_reveal(result.path)
        else:
            self._on_file_open(result.path)

    def _on_key_pressed(self, _controller, keyval: int, _keycode: int, _state) -> bool:
        if keyval == Gdk.KEY_Escape:
            self.entry.set_text("")
            self.results_panel.set_visible(False)
            return True
        if not self._rows:
            return False
        selected = self.list_box.get_selected_row()
        index = self._rows.index(selected) if selected in self._rows else 0
        if keyval in (Gdk.KEY_Down, Gdk.KEY_Up):
            delta = 1 if keyval == Gdk.KEY_Down else -1
            next_index = max(0, min(len(self._rows) - 1, index + delta))
            self.list_box.select_row(self._rows[next_index])
            return True
        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            self._on_row_activated(self.list_box, self._rows[index])
            return True
        return False

    def _clear_results(self, message: str) -> None:
        self._clear_rows()
        self.status.set_text(message)

    def _clear_rows(self) -> None:
        for row in self._rows:
            self.list_box.remove(row)
        self._rows.clear()
        self._results.clear()


def _highlight(text: str, indices: tuple[int, ...]) -> str:
    if not indices:
        return GLib.markup_escape_text(text)
    selected = set(indices)
    chunks: list[str] = []
    open_match = False
    for index, character in enumerate(text):
        matched = index in selected
        if matched and not open_match:
            chunks.append("<b>")
        if not matched and open_match:
            chunks.append("</b>")
        chunks.append(GLib.markup_escape_text(character))
        open_match = matched
    if open_match:
        chunks.append("</b>")
    return "".join(chunks)
