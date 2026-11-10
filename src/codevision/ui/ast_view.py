from __future__ import annotations

import hashlib
import threading
from collections.abc import Callable
from pathlib import Path

import gi

gi.require_version("Gio", "2.0")
gi.require_version("GLib", "2.0")
gi.require_version("GObject", "2.0")
gi.require_version("Gtk", "4.0")
gi.require_version("Pango", "1.0")
from gi.repository import Gio, GLib, GObject, Gtk, Pango

from ..analysis import ASTAnalyzer, ASTStatistics
from ..model import ASTNode, ASTResult
from ..parser import SourceParser


class _ASTTreeItem(GObject.Object):
    __gtype_name__ = "CodeVisionASTTreeItem"

    def __init__(self, node: ASTNode) -> None:
        super().__init__()
        self.node = node
        self.children = Gio.ListStore.new(_ASTTreeItem)
        self.children_loaded = False


class ASTView(Gtk.Box):
    """Interactive AST tree, details, and source-navigation view."""

    def __init__(
        self,
        on_source_navigate: Callable[[ASTNode], None] | None = None,
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add_css_class("ast-view")
        self.set_hexpand(True)
        self.set_vexpand(True)
        self._on_source_navigate = on_source_navigate
        self._parser = SourceParser()
        self._analyzer = ASTAnalyzer()
        self._generation = 0
        self._timeout_id = 0
        self._source_hash: str | None = None
        self._result: ASTResult | None = None
        self._statistics: ASTStatistics | None = None
        self._selected_node_id: str | None = None
        self._node_by_id: dict[str, ASTNode] = {}
        self._results_cache: dict[
            str, tuple[ASTResult, ASTStatistics, dict[str, ASTNode]]
        ] = {}
        self._tree_model: Gtk.TreeListModel | None = None
        self._selection: Gtk.SingleSelection | None = None
        self._search_matches: tuple[str, ...] = ()
        self._search_index = -1

        search_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        search_row.set_hexpand(True)
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search AST nodes...")
        self.search_entry.add_css_class("ast-search")
        self.search_entry.set_hexpand(True)
        self.search_entry.connect("search-changed", self._on_search_changed)
        search_row.append(self.search_entry)
        self._previous_match_button = Gtk.Button(label="‹")
        self._previous_match_button.set_tooltip_text("Previous match")
        self._previous_match_button.connect("clicked", self._previous_match)
        search_row.append(self._previous_match_button)
        self._next_match_button = Gtk.Button(label="›")
        self._next_match_button.set_tooltip_text("Next match")
        self._next_match_button.connect("clicked", self._next_match)
        search_row.append(self._next_match_button)
        self._match_count = Gtk.Label(label="")
        self._match_count.add_css_class("ast-summary")
        search_row.append(self._match_count)
        self.append(search_row)

        self.summary = Gtk.Label(label="Open a C or C++ source file to inspect its AST.")
        self.summary.set_halign(Gtk.Align.START)
        self.summary.add_css_class("ast-summary")
        self.append(self.summary)

        self.content_stack = Gtk.Stack()
        self.content_stack.set_transition_type(Gtk.StackTransitionType.NONE)
        self.content_stack.set_hexpand(True)
        self.content_stack.set_vexpand(True)
        self._state_label = Gtk.Label()
        self._state_label.set_wrap(True)
        self._state_label.set_halign(Gtk.Align.CENTER)
        self._state_label.set_valign(Gtk.Align.CENTER)
        self._state_label.add_css_class("ast-empty-state")
        self.content_stack.add_named(self._state_label, "state")

        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        body.set_hexpand(True)
        body.set_vexpand(True)

        self.tree_scroller = Gtk.ScrolledWindow()
        self.tree_scroller.set_policy(
            Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC
        )
        self.tree_scroller.set_hexpand(True)
        self.tree_scroller.set_vexpand(True)
        tree_actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self._expand_button = Gtk.Button(label="Expand All")
        self._expand_button.connect("clicked", self._expand_all)
        tree_actions.append(self._expand_button)
        self._collapse_button = Gtk.Button(label="Collapse All")
        self._collapse_button.connect("clicked", self._collapse_all)
        tree_actions.append(self._collapse_button)
        body.append(tree_actions)
        body.append(self.tree_scroller)

        details = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        details.add_css_class("ast-details")
        self._detail_name = Gtk.Label(label="Select a node to view its details")
        self._detail_name.set_halign(Gtk.Align.START)
        self._detail_name.add_css_class("ast-detail-name")
        details.append(self._detail_name)
        self._detail_type = self._detail_label(details, "Type: —")
        self._detail_location = self._detail_label(details, "Location: —")
        self._detail_children = self._detail_label(details, "Children: —")
        self._detail_source = Gtk.Label(label="Source: —")
        self._detail_source.set_halign(Gtk.Align.START)
        self._detail_source.set_wrap(True)
        self._detail_source.set_selectable(True)
        self._detail_source.add_css_class("ast-detail-source")
        details.append(self._detail_source)
        self._detail_error = self._detail_label(details, "")
        self._navigate_button = Gtk.Button(label="Go to Source")
        self._navigate_button.set_halign(Gtk.Align.START)
        self._navigate_button.set_sensitive(False)
        self._navigate_button.connect("clicked", self._on_navigate_clicked)
        details.append(self._navigate_button)
        body.append(details)

        self.content_stack.add_named(body, "tree")
        self.append(self.content_stack)
        self._show_state("Open a C or C++ source file to inspect its AST.")

    @property
    def result(self) -> ASTResult | None:
        return self._result

    @staticmethod
    def _detail_label(parent: Gtk.Box, text: str) -> Gtk.Label:
        label = Gtk.Label(label=text)
        label.set_halign(Gtk.Align.START)
        label.set_wrap(True)
        label.add_css_class("ast-detail")
        parent.append(label)
        return label

    def set_source(
        self,
        source: str | None,
        file_path: Path | None,
        language: str | None = None,
    ) -> None:
        self._generation += 1
        generation = self._generation
        if self._timeout_id:
            GLib.source_remove(self._timeout_id)
            self._timeout_id = 0
        self._search_matches = ()
        self._search_index = -1
        self._match_count.set_text("")
        if source is None:
            self._source_hash = None
            self._result = None
            self._statistics = None
            self._reset_details()
            self._show_state("No source editor is active.")
            self.summary.set_text("AST analysis follows the active source editor.")
            return

        self.summary.set_text("Parsing active source...")
        self._show_state("Parsing active source...")
        self._timeout_id = GLib.timeout_add(
            250, self._start_parse, generation, source, file_path, language
        )

    def _start_parse(
        self,
        generation: int,
        source: str,
        file_path: Path | None,
        language: str | None,
    ) -> bool:
        self._timeout_id = 0
        worker = threading.Thread(
            target=self._hash_source,
            args=(generation, source, file_path, language),
            daemon=True,
            name="codevision-ast-parser",
        )
        worker.start()
        return GLib.SOURCE_REMOVE

    def _hash_source(
        self,
        generation: int,
        source: str,
        file_path: Path | None,
        language: str | None,
    ) -> None:
        source_hash = hashlib.sha256(
            (str(file_path or "") + "\0" + (language or "") + "\0" + source).encode(
                "utf-8"
            )
        ).hexdigest()
        GLib.idle_add(
            self._check_cache_or_parse,
            generation,
            source_hash,
            source,
            file_path,
            language,
        )

    def _check_cache_or_parse(
        self,
        generation: int,
        source_hash: str,
        source: str,
        file_path: Path | None,
        language: str | None,
    ) -> bool:
        if generation != self._generation:
            return GLib.SOURCE_REMOVE
        if source_hash == self._source_hash and self._result is not None:
            self._set_summary(self._result, self._statistics)
            self.content_stack.set_visible_child_name("tree")
            return GLib.SOURCE_REMOVE
        cached = self._results_cache.get(source_hash)
        if cached is not None:
            result, stats, nodes_by_id = cached
            self._apply_result(
                generation, source_hash, result, stats, nodes_by_id
            )
            return GLib.SOURCE_REMOVE
        worker = threading.Thread(
            target=self._parse_in_worker,
            args=(generation, source_hash, source, file_path, language),
            daemon=True,
            name="codevision-ast-parser",
        )
        worker.start()
        return GLib.SOURCE_REMOVE

    def _parse_in_worker(
        self,
        generation: int,
        source_hash: str,
        source: str,
        file_path: Path | None,
        language: str | None,
    ) -> None:
        try:
            result = self._parser.parse(
                source, language=language, file_path=file_path
            )
            stats = self._analyzer.statistics(result)
            nodes_by_id = {node.node_id: node for node in result.root.walk()}
        except (RuntimeError, TypeError, ValueError) as error:
            GLib.idle_add(
                self._apply_error, generation, source_hash, str(error)
            )
            return
        GLib.idle_add(
            self._apply_result,
            generation,
            source_hash,
            result,
            stats,
            nodes_by_id,
        )

    def _apply_error(
        self, generation: int, source_hash: str, message: str
    ) -> bool:
        if generation != self._generation:
            return GLib.SOURCE_REMOVE
        self._result = None
        self._statistics = None
        self._source_hash = source_hash
        self._show_state(message)
        self.summary.set_text("AST analysis unavailable.")
        return GLib.SOURCE_REMOVE

    def _apply_result(
        self,
        generation: int,
        source_hash: str,
        result: ASTResult,
        stats: ASTStatistics | None = None,
        nodes_by_id: dict[str, ASTNode] | None = None,
    ) -> bool:
        if generation != self._generation:
            return GLib.SOURCE_REMOVE
        if stats is None:
            stats = self._analyzer.statistics(result)
        self._result = result
        self._statistics = stats
        self._source_hash = source_hash
        if nodes_by_id is None:
            nodes_by_id = {node.node_id: node for node in result.root.walk()}
        self._results_cache[source_hash] = (result, stats, nodes_by_id)
        if len(self._results_cache) > 3:
            self._results_cache.pop(next(iter(self._results_cache)))
        self._node_by_id = nodes_by_id
        self._reset_details()
        self._search_matches = ()
        self._search_index = -1
        self._match_count.set_text("")

        root_store = Gio.ListStore.new(_ASTTreeItem)
        root_store.append(_ASTTreeItem(result.root))
        tree_model = Gtk.TreeListModel.new(
            root_store, False, False, self._create_children
        )
        selection = Gtk.SingleSelection.new(tree_model)
        selection.set_autoselect(False)
        selection.set_can_unselect(True)
        selection.connect("notify::selected-item", self._on_selection_changed)
        factory = Gtk.SignalListItemFactory.new()
        factory.connect("setup", self._setup_list_item)
        factory.connect("bind", self._bind_list_item)
        list_view = Gtk.ListView.new(selection, factory)
        list_view.add_css_class("ast-tree")
        self.tree_scroller.set_child(list_view)
        self._tree_model = tree_model
        self._selection = selection

        self._set_summary(result, stats)
        self.content_stack.set_visible_child_name("tree")
        if result.syntax_error_count:
            self._detail_error.set_text(
                f"The syntax tree contains {result.syntax_error_count} syntax errors."
            )
        return GLib.SOURCE_REMOVE

    def _set_summary(
        self, result: ASTResult, stats: ASTStatistics | None
    ) -> None:
        if stats is None:
            return
        status = "Partial AST" if result.is_partial else "AST ready"
        self.summary.set_text(
            f"{status} · {stats.total_nodes} nodes · {stats.functions} functions · "
            f"{stats.syntax_errors} syntax errors · {result.parse_duration_ms:.1f} ms"
        )

    @staticmethod
    def _create_children(item: _ASTTreeItem) -> Gio.ListStore | None:
        if not item.node.children:
            return None
        if not item.children_loaded:
            for child in item.node.children:
                item.children.append(_ASTTreeItem(child))
            item.children_loaded = True
        return item.children

    @staticmethod
    def _setup_list_item(_factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem) -> None:
        expander = Gtk.TreeExpander()
        label = Gtk.Label()
        label.set_halign(Gtk.Align.START)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.add_css_class("ast-node-label")
        expander.set_child(label)
        list_item.set_child(expander)

    def _bind_list_item(
        self, _factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem
    ) -> None:
        row = list_item.get_item()
        expander = list_item.get_child()
        if not isinstance(row, Gtk.TreeListRow) or not isinstance(expander, Gtk.TreeExpander):
            return
        item = row.get_item()
        label = expander.get_child()
        if not isinstance(item, _ASTTreeItem) or not isinstance(label, Gtk.Label):
            return
        expander.set_list_row(row)
        label.set_text(item.node.display_name)
        label.remove_css_class("ast-error-node")
        kind_classes = (
            "ast-node-function",
            "ast-node-control",
            "ast-node-declaration",
            "ast-node-identifier",
            "ast-node-default",
        )
        for kind in kind_classes:
            label.remove_css_class(kind)
        kind_class = (
            "ast-node-function"
            if "function" in item.node.node_type or item.node.node_type == "call_expression"
            else "ast-node-control"
            if item.node.node_type.endswith("_statement")
            else "ast-node-declaration"
            if "declaration" in item.node.node_type or item.node.node_type.endswith("_specifier")
            else "ast-node-identifier"
            if item.node.node_type == "identifier"
            else "ast-node-default"
        )
        label.add_css_class(kind_class)
        if item.node.has_error or item.node.is_missing:
            label.add_css_class("ast-error-node")

    def _on_selection_changed(
        self, selection: Gtk.SingleSelection, _property: GObject.ParamSpec
    ) -> None:
        row = selection.get_selected_item()
        if not isinstance(row, Gtk.TreeListRow):
            self._reset_details()
            return
        item = row.get_item()
        if isinstance(item, _ASTTreeItem):
            self._show_details(item.node)
            if (
                item.node.location.has_range
                and self._on_source_navigate is not None
            ):
                self._on_source_navigate(item.node)

    def _expand_all(self, _button: Gtk.Button) -> None:
        model = self._tree_model
        if model is None:
            return
        index = 0
        while index < model.get_n_items():
            row = model.get_item(index)
            if isinstance(row, Gtk.TreeListRow) and row.is_expandable():
                row.set_expanded(True)
            index += 1

    def _collapse_all(self, _button: Gtk.Button) -> None:
        if self._tree_model is None or self._tree_model.get_n_items() == 0:
            return
        root = self._tree_model.get_item(0)
        if isinstance(root, Gtk.TreeListRow):
            root.set_expanded(False)

    def _show_details(self, node: ASTNode) -> None:
        location = node.location
        self._detail_name.set_text(node.display_name)
        self._detail_type.set_text(f"Type: {node.node_type}")
        self._detail_location.set_text(
            f"Location: {location.start_line}:{location.start_column}–"
            f"{location.end_line}:{location.end_column}"
        )
        self._detail_children.set_text(f"Children: {node.child_count}")
        self._detail_source.set_text(f"Source: {node.source_text or '(no source text)'}")
        error = "Missing syntax node" if node.is_missing else (
            "Syntax error" if node.has_error else ""
        )
        self._detail_error.set_text(error)
        self._navigate_button.set_sensitive(
            location.has_range and self._on_source_navigate is not None
        )
        self._selected_node_id = node.node_id

    def _reset_details(self) -> None:
        self._detail_name.set_text("Select a node to view its details")
        self._detail_type.set_text("Type: —")
        self._detail_location.set_text("Location: —")
        self._detail_children.set_text("Children: —")
        self._detail_source.set_text("Source: —")
        self._detail_error.set_text("")
        self._navigate_button.set_sensitive(False)
        self._selected_node_id = None

    def _on_navigate_clicked(self, _button: Gtk.Button) -> None:
        node_id = getattr(self, "_selected_node_id", None)
        node = self._node_by_id.get(node_id) if node_id is not None else None
        if node is not None and node.location.has_range and self._on_source_navigate:
            self._on_source_navigate(node)

    def _on_search_changed(self, _entry: Gtk.SearchEntry) -> None:
        if self._result is None or self._tree_model is None or self._selection is None:
            return
        query = self.search_entry.get_text().strip().casefold()
        if not query:
            self._search_matches = ()
            self._search_index = -1
            self._match_count.set_text("")
            return
        nodes = tuple(self._result.root.walk())
        matches = tuple(
            node.node_id
            for node in nodes
            if query in node.display_name.casefold()
            or query in node.node_type.casefold()
        )
        if not matches:
            matches = tuple(
                node.node_id
                for node in nodes
                if query in node.source_text.casefold()
            )
        self._search_matches = matches
        self._search_index = 0 if matches else -1
        self._match_count.set_text(
            f"{len(matches)} results" if matches else "0 results"
        )
        if not matches:
            self._detail_name.set_text(f"No AST nodes match “{query}”.")
            return
        self._select_search_match()

    def _previous_match(self, _button: Gtk.Button) -> None:
        if self._search_matches:
            self._search_index = (self._search_index - 1) % len(self._search_matches)
            self._select_search_match()

    def _next_match(self, _button: Gtk.Button) -> None:
        if self._search_matches:
            self._search_index = (self._search_index + 1) % len(self._search_matches)
            self._select_search_match()

    def _select_search_match(self) -> None:
        if (
            self._tree_model is None
            or self._selection is None
            or not self._search_matches
        ):
            return
        match = self._node_by_id[self._search_matches[self._search_index]]
        ancestors: list[str] = []
        parent_id = match.parent_id
        while parent_id is not None:
            ancestors.append(parent_id)
            parent_id = self._node_by_id[parent_id].parent_id
        for ancestor_id in reversed(ancestors):
            index = self._visible_index(ancestor_id)
            if index >= 0:
                row = self._tree_model.get_item(index)
                if isinstance(row, Gtk.TreeListRow):
                    row.set_expanded(True)
        index = self._visible_index(match.node_id)
        if index >= 0:
            self._selection.set_selected(index)
            GLib.idle_add(self._scroll_to_index, index)

    def _scroll_to_index(self, index: int) -> bool:
        adjustment = self.tree_scroller.get_vadjustment()
        target = min(
            max(0.0, index * 24.0),
            max(0.0, adjustment.get_upper() - adjustment.get_page_size()),
        )
        adjustment.set_value(target)
        return GLib.SOURCE_REMOVE

    def _visible_index(self, node_id: str) -> int:
        if self._tree_model is None:
            return -1
        for index in range(self._tree_model.get_n_items()):
            row = self._tree_model.get_item(index)
            if isinstance(row, Gtk.TreeListRow):
                item = row.get_item()
                if isinstance(item, _ASTTreeItem) and item.node.node_id == node_id:
                    return index
        return -1

    def _show_state(self, message: str) -> None:
        self._state_label.set_text(message)
        self.content_stack.set_visible_child_name("state")


__all__ = ["ASTView"]
