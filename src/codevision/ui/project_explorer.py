from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk

from ..services.folder_browser import FolderBrowserService
from .explorer_actions.collapse_all import CollapseAllAction
from .explorer_actions.new_file import NewFileAction
from .explorer_actions.new_folder import NewFolderAction
from .explorer_actions.refresh import RefreshAction
from .widgets.folder import FolderPickerWindow


class ProjectExplorer(Gtk.Box):
    """Folder-backed project explorer with file and directory actions."""

    def __init__(self, on_file_open: Callable[[Path], None]) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_name("project-tree")
        self.add_css_class("panel")
        self.set_size_request(220, -1)
        self._on_file_open = on_file_open
        self._root_path: Path | None = None
        self._folder_browser = FolderBrowserService()
        self._folder_picker: FolderPickerWindow | None = None

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header.set_margin_top(10)
        header.set_margin_bottom(8)
        header.set_margin_start(12)
        header.set_margin_end(8)
        header.add_css_class("panel-header")

        title = Gtk.Label(label="Project Explorer")
        title.set_halign(Gtk.Align.START)
        title.set_hexpand(True)
        title.add_css_class("section-title")
        header.append(title)
        self.append(header)

        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        actions.add_css_class("explorer-actions")

        open_folder_button = Gtk.Button(label="Open Folder...")
        open_folder_button.set_halign(Gtk.Align.START)
        open_folder_button.set_tooltip_text("Choose a project folder")
        open_folder_button.add_css_class("explorer-open-folder")
        open_folder_button.connect("clicked", lambda *_args: self.open_folder())
        actions.append(open_folder_button)

        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        actions.append(spacer)

        self.new_folder_action = NewFolderAction(
            self,
            self._get_target_directory,
            self._on_folder_created,
        )
        self.refresh_action = RefreshAction(
            self.refresh
        )
        self.collapse_all_action = CollapseAllAction(
            self._collapse_all
        )
        self.new_file_action = NewFileAction(
            self,
            self._get_target_directory,
            self._on_file_created,
        )
        actions.append(self.new_folder_action)
        actions.append(self.new_file_action)
        actions.append(self.refresh_action)
        actions.append(self.collapse_all_action)
        self.append(actions)

        self._store = Gtk.TreeStore(str, str, bool, bool, str, bool)
        self.tree = Gtk.TreeView(model=self._store)
        self.tree.set_name("project-tree")
        self.tree.set_headers_visible(False)
        self.tree.set_enable_search(True)
        self.tree.set_activate_on_single_click(True)
        self.tree.set_hexpand(True)
        self.tree.set_vexpand(True)
        self.tree.connect("row-expanded", self._on_row_expanded)
        self.tree.connect("row-activated", self._on_row_activated)
        click_controller = Gtk.GestureClick.new()
        click_controller.connect("pressed", self._on_tree_pressed)
        self.tree.add_controller(click_controller)

        column = Gtk.TreeViewColumn()
        icon = Gtk.CellRendererPixbuf()
        icon.set_property("xpad", 4)
        column.pack_start(icon, False)
        column.add_attribute(icon, "icon-name", 4)
        column.add_attribute(icon, "visible", 5)

        text = Gtk.CellRendererText()
        text.set_property("ellipsize", 3)
        column.pack_start(text, True)
        column.add_attribute(text, "text", 0)
        column.add_attribute(text, "visible", 5)
        column.set_expand(True)
        self.tree.append_column(column)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_child(self.tree)

        self.empty_state = Gtk.Label(label="Open a folder to browse its files")
        self.empty_state.set_wrap(True)
        self.empty_state.set_valign(Gtk.Align.START)
        self.empty_state.add_css_class("explorer-empty")

        self.content = Gtk.Stack()
        self.content.set_vexpand(True)
        self.content.add_named(self.empty_state, "empty")
        self.content.add_named(scrolled, "tree")
        self.content.set_visible_child_name("empty")
        self.append(self.content)
        self._set_project_action_state(False)

    def _set_project_action_state(self, enabled: bool) -> None:
        self.refresh_action.set_sensitive(enabled)
        self.collapse_all_action.set_sensitive(enabled)

    def open_folder(self) -> None:
        parent = self.get_root()
        parent_window = parent if isinstance(parent, Gtk.Window) else None
        if self._folder_picker is not None and self._folder_picker.get_visible():
            self._folder_picker.present()
            return

        self._folder_picker = FolderPickerWindow(
            parent=parent_window,
            initial_directory=self._root_path or Path.home(),
            on_folder_opened=self._set_project_folder,
            on_file_opened=self._open_file_from_picker,
            service=self._folder_browser,
        )
        self._folder_picker.connect("close-request", self._on_folder_picker_closed)
        self._folder_picker.present()

    def _on_folder_picker_closed(self, window: Gtk.Window) -> bool:
        if self._folder_picker is window:
            self._folder_picker = None
        return False

    def _open_file_from_picker(self, path: Path) -> None:
        if not path.is_file():
            return
        if self._root_path is None or not path.is_relative_to(self._root_path):
            self._set_project_folder(path.parent)
        self._on_file_open(path)

    def _get_target_directory(self) -> Path:
        if self._root_path is None:
            return Path.cwd()

        _model, selected_iter = self.tree.get_selection().get_selected()
        if selected_iter is None:
            return self._root_path

        selected_path = Path(self._store.get_value(selected_iter, 1))
        if self._store.get_value(selected_iter, 2):
            return selected_path
        return selected_path.parent

    def _on_tree_pressed(
        self,
        _gesture: Gtk.GestureClick,
        _press_count: int,
        x: float,
        y: float,
    ) -> None:
        if self.tree.get_path_at_pos(int(x), int(y)) is None:
            self.tree.get_selection().unselect_all()

    def _on_file_created(self, path: Path) -> None:
        if self._root_path is None:
            self._set_project_folder(path.parent)
        else:
            self._insert_created_entry(path)
        self._on_file_open(path)

    def _on_folder_created(self, path: Path) -> None:
        if self._root_path is None:
            self._set_project_folder(path)
        else:
            self._insert_created_entry(path)

    def _insert_created_entry(self, path: Path) -> None:
        parent_path = path.parent.resolve()
        parent_iter = self._find_path_iter(parent_path)
        if parent_iter is None:
            self.refresh()
            return

        if not self._store.get_value(parent_iter, 3):
            self._load_directory(parent_iter, parent_path)
            return

        is_directory = path.is_dir()
        new_key = (not is_directory, path.name.casefold())
        sibling = None
        for index in range(self._store.iter_n_children(parent_iter)):
            child_iter = self._store.iter_nth_child(parent_iter, index)
            if child_iter is None:
                continue
            child_key = (
                not self._store.get_value(child_iter, 2),
                self._store.get_value(child_iter, 0).casefold(),
            )
            if new_key < child_key:
                sibling = child_iter
                break

        row_iter = self._store.insert_before(parent_iter, sibling)
        self._store.set(
            row_iter,
            [0, 1, 2, 3, 4, 5],
            [
                path.name,
                str(path),
                is_directory,
                False,
                "folder-symbolic" if is_directory else "text-x-generic-symbolic",
                True,
            ],
        )
        if is_directory:
            self._store.append(row_iter, ["", "", False, True, "", False])

    def _set_project_folder(self, path: Path) -> None:
        self._root_path = path.resolve()
        self._store.clear()
        root_iter = self._store.append(
            None,
            [self._root_path.name, str(self._root_path), True, False, "folder-symbolic", True],
        )
        self._load_directory(root_iter, self._root_path)
        self.tree.expand_row(self._store.get_path(root_iter), False)
        self.content.set_visible_child_name("tree")
        self._set_project_action_state(True)

    def _load_directory(self, parent_iter: Gtk.TreeIter, path: Path) -> None:
        while self._store.iter_children(parent_iter) is not None:
            child_iter = self._store.iter_children(parent_iter)
            if child_iter is not None:
                self._store.remove(child_iter)

        try:
            entries = self._folder_browser.list_entries(path, show_hidden=True)
        except OSError:
            self._store.set_value(parent_iter, 3, True)
            return

        for entry in entries:
            icon_name = (
                "folder-symbolic"
                if entry.is_directory
                else "text-x-generic-symbolic"
            )
            child_iter = self._store.append(
                parent_iter,
                [
                    entry.name,
                    str(entry.path),
                    entry.is_directory,
                    False,
                    icon_name,
                    True,
                ],
            )
            if entry.is_directory:
                self._store.append(child_iter, ["", "", False, True, "", False])

        self._store.set_value(parent_iter, 3, True)

    def _on_row_expanded(
        self, tree: Gtk.TreeView, row_iter: Gtk.TreeIter, path: Gtk.TreePath
    ) -> None:
        if self._store.get_value(row_iter, 2) and not self._store.get_value(row_iter, 3):
            GLib.idle_add(self._load_expanded_directory, path.copy())

    def _load_expanded_directory(self, path: Gtk.TreePath) -> bool:
        row_iter = self._store.get_iter(path)
        if self._store.get_value(row_iter, 2):
            if not self._store.get_value(row_iter, 3):
                self._load_directory(
                    row_iter, Path(self._store.get_value(row_iter, 1))
                )
            self.tree.expand_row(path, False)
        return GLib.SOURCE_REMOVE

    def _on_row_activated(
        self, tree: Gtk.TreeView, path: Gtk.TreePath, column: Gtk.TreeViewColumn
    ) -> None:
        if column not in tree.get_columns():
            return

        row_iter = self._store.get_iter(path)
        if self._store.get_value(row_iter, 2):
            if tree.row_expanded(path):
                tree.collapse_row(path)
            else:
                tree.expand_row(path, False)
            return

        file_path = self._store.get_value(row_iter, 1)
        path = Path(file_path)
        if path.is_file():
            self._on_file_open(path)

    def refresh(self) -> None:
        if self._root_path is not None:
            expanded_paths = self._expanded_directory_paths()
            self._set_project_folder(self._root_path)
            for directory in sorted(expanded_paths, key=lambda path: len(path.parts)):
                row_iter = self._find_path_iter(directory)
                if row_iter is not None:
                    self.tree.expand_row(self._store.get_path(row_iter), False)

    def _expanded_directory_paths(self) -> set[Path]:
        expanded: set[Path] = set()
        root_iter = self._store.get_iter_first()
        if root_iter is None:
            return expanded

        def visit(row_iter: Gtk.TreeIter) -> None:
            row_path = self._store.get_path(row_iter)
            if self.tree.row_expanded(row_path):
                if self._store.get_value(row_iter, 2):
                    expanded.add(Path(self._store.get_value(row_iter, 1)))

                for index in range(self._store.iter_n_children(row_iter)):
                    child_iter = self._store.iter_nth_child(row_iter, index)
                    if child_iter is not None:
                        visit(child_iter)

        visit(root_iter)
        return expanded

    def _find_path_iter(self, target: Path) -> Gtk.TreeIter | None:
        if self._root_path is None or not target.is_relative_to(self._root_path):
            return None

        row_iter = self._store.get_iter_first()
        if row_iter is None:
            return None

        for part in target.relative_to(self._root_path).parts:
            match = None
            for index in range(self._store.iter_n_children(row_iter)):
                child_iter = self._store.iter_nth_child(row_iter, index)
                if (
                    child_iter is not None
                    and self._store.get_value(child_iter, 0) == part
                ):
                    match = child_iter
                    break
            if match is None:
                return None
            row_iter = match

        return row_iter

    def _collapse_all(self) -> None:
        if self._root_path is not None:
            self.tree.collapse_all()
