from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from ..services.folder_browser import FolderBrowserService
from .widgets.folder import FolderPickerWindow


class ProjectExplorer(Gtk.Box):
    """Folder-backed project explorer with file and directory actions."""

    def __init__(self, on_file_open: Callable[[Path], None]) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_name("project-panel")
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

        self._action_buttons: list[Gtk.Button] = []
        self._add_action(actions, "document-new-symbolic", "New File", self._new_file)
        self._add_action(
            actions, "folder-new-symbolic", "New Folder", self._new_folder
        )
        self._add_action(actions, "view-refresh-symbolic", "Refresh", self.refresh)
        self._add_action(
            actions, "view-list-symbolic", "Collapse All", self._collapse_all
        )
        self.append(actions)

        self._store = Gtk.TreeStore(str, str, bool, bool, str, bool)
        self.tree = Gtk.TreeView(model=self._store)
        self.tree.set_name("project-tree")
        self.tree.set_headers_visible(False)
        self.tree.set_enable_search(True)
        self.tree.set_activate_on_single_click(False)
        self.tree.set_hexpand(True)
        self.tree.set_vexpand(True)
        self.tree.connect("row-expanded", self._on_row_expanded)
        self.tree.connect("row-activated", self._on_row_activated)

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

        self._set_project_actions_enabled(False)

    def _add_action(
        self,
        container: Gtk.Box,
        icon_name: str,
        tooltip: str,
        callback: Callable[[], None],
    ) -> None:
        button = Gtk.Button()
        button.set_child(Gtk.Image.new_from_icon_name(icon_name))
        button.set_tooltip_text(tooltip)
        button.add_css_class("explorer-action")
        button.connect("clicked", lambda *_args: callback())
        self._action_buttons.append(button)
        container.append(button)

    def _set_project_actions_enabled(self, enabled: bool) -> None:
        for button in self._action_buttons:
            button.set_sensitive(enabled)

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
            on_file_opened=self._on_file_open,
            service=self._folder_browser,
        )
        self._folder_picker.connect("close-request", self._on_folder_picker_closed)
        self._folder_picker.present()

    def _on_folder_picker_closed(self, window: Gtk.Window) -> bool:
        if self._folder_picker is window:
            self._folder_picker = None
        return False

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
        self._set_project_actions_enabled(True)

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
        if (
            tree.row_expanded(path)
            and self._store.get_value(row_iter, 2)
            and not self._store.get_value(row_iter, 3)
        ):
            self._load_directory(row_iter, Path(self._store.get_value(row_iter, 1)))

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
        if file_path:
            self._on_file_open(Path(file_path))

    def _new_file(self) -> None:
        self._prompt_new_item("New File", is_directory=False)

    def _new_folder(self) -> None:
        self._prompt_new_item("New Folder", is_directory=True)

    def _prompt_new_item(self, title: str, is_directory: bool) -> None:
        if self._root_path is None:
            return

        root = self.get_root()
        parent = root if isinstance(root, Gtk.Window) else None
        dialog = Gtk.Dialog(title=title, transient_for=parent, modal=True)
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("Create", Gtk.ResponseType.ACCEPT)

        content = dialog.get_content_area()
        content.set_spacing(8)
        content.set_margin_top(12)
        content.set_margin_bottom(12)
        content.set_margin_start(12)
        content.set_margin_end(12)

        entry = Gtk.Entry()
        entry.set_placeholder_text("Name")
        entry.set_activates_default(True)
        content.append(entry)

        error_label = Gtk.Label()
        error_label.set_halign(Gtk.Align.START)
        error_label.add_css_class("explorer-error")
        error_label.set_visible(False)
        content.append(error_label)

        def on_response(dialog: Gtk.Dialog, response: int) -> None:
            if response != Gtk.ResponseType.ACCEPT:
                dialog.close()
                return

            name = entry.get_text().strip()
            if not name or Path(name).name != name or name in {".", ".."}:
                error_label.set_text("Enter a valid name")
                error_label.set_visible(True)
                return

            target = self._root_path / name
            try:
                if is_directory:
                    target.mkdir()
                else:
                    target.touch(exist_ok=False)
            except OSError as error:
                error_label.set_text(str(error))
                error_label.set_visible(True)
                return

            dialog.close()
            self.refresh()

        dialog.connect("response", on_response)
        dialog.present()
        entry.grab_focus()

    def refresh(self) -> None:
        if self._root_path is not None:
            self._set_project_folder(self._root_path)

    def _collapse_all(self) -> None:
        self.tree.collapse_all()
