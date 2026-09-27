from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gtk

from ...services.folder_browser import BrowserEntry, FolderBrowserService


class FolderPickerWindow(Gtk.Window):
    """In-app folder browser with hover and keyboard activation."""

    def __init__(
        self,
        parent: Gtk.Window | None,
        initial_directory: Path,
        on_folder_opened: Callable[[Path], None],
        on_file_opened: Callable[[Path], None],
        service: FolderBrowserService | None = None,
    ) -> None:
        super().__init__()
        self.set_title("Open Folder")
        self.set_default_size(680, 500)
        self.set_size_request(480, 340)
        self.set_resizable(True)
        self.set_modal(True)
        if parent is not None:
            self.set_transient_for(parent)
        self.set_name("folder-picker-window")

        self._service = service or FolderBrowserService()
        self._on_folder_opened = on_folder_opened
        self._on_file_opened = on_file_opened
        self._current_directory = initial_directory.expanduser()
        self._entries_by_row: dict[Gtk.ListBoxRow, BrowserEntry] = {}
        self._hovered_row: Gtk.ListBoxRow | None = None

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_child(root)

        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        toolbar.set_margin_top(12)
        toolbar.set_margin_bottom(12)
        toolbar.set_margin_start(12)
        toolbar.set_margin_end(12)
        toolbar.add_css_class("folder-picker-toolbar")

        heading = Gtk.Label(label="Browse folders")
        heading.set_halign(Gtk.Align.START)
        heading.add_css_class("folder-picker-heading")
        toolbar.append(heading)

        self.path_label = Gtk.Label()
        self.path_label.set_halign(Gtk.Align.START)
        self.path_label.set_hexpand(True)
        self.path_label.set_ellipsize(3)
        self.path_label.add_css_class("folder-picker-path")
        toolbar.append(self.path_label)

        self.up_button = Gtk.Button()
        self.up_button.set_child(Gtk.Image.new_from_icon_name("go-up-symbolic"))
        self.up_button.set_tooltip_text("Go to parent folder")
        self.up_button.add_css_class("folder-picker-icon-button")
        self.up_button.connect("clicked", lambda *_args: self._navigate_up())
        toolbar.append(self.up_button)
        root.append(toolbar)

        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.list_box.set_activate_on_single_click(False)
        self.list_box.add_css_class("folder-picker-list")
        self.list_box.connect("row-activated", self._on_row_activated)

        empty_label = Gtk.Label(label="This folder is empty")
        empty_label.add_css_class("folder-picker-empty")
        self.list_box.set_placeholder(empty_label)

        hover_controller = Gtk.EventControllerMotion.new()
        hover_controller.connect("motion", self._on_pointer_motion)
        hover_controller.connect("leave", self._on_pointer_leave)
        self.list_box.add_controller(hover_controller)

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_vexpand(True)
        scroller.set_child(self.list_box)
        root.append(scroller)

        self.status = Gtk.Label()
        self.status.set_halign(Gtk.Align.START)
        self.status.add_css_class("folder-picker-status")

        footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        footer.set_margin_top(10)
        footer.set_margin_bottom(12)
        footer.set_margin_start(12)
        footer.set_margin_end(12)
        footer.append(self.status)

        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        footer.append(spacer)

        cancel_button = Gtk.Button(label="Cancel")
        cancel_button.connect("clicked", lambda *_args: self.close())
        footer.append(cancel_button)

        open_button = Gtk.Button(label="Open Folder")
        open_button.add_css_class("suggested-action")
        open_button.connect("clicked", lambda *_args: self._open_current_folder())
        footer.append(open_button)
        root.append(footer)

        key_controller = Gtk.EventControllerKey.new()
        key_controller.connect("key-pressed", self._on_key_pressed)
        self.add_controller(key_controller)

        self._navigate(self._current_directory)

    def _navigate(self, directory: Path) -> None:
        try:
            directory = directory.expanduser().resolve(strict=True)
            entries = self._service.list_entries(directory)
        except OSError as error:
            self.status.set_text(str(error))
            return

        self._current_directory = directory
        self.path_label.set_text(str(directory))
        self.status.set_text(f"{len(entries)} items")
        self.up_button.set_sensitive(
            self._service.parent_directory(directory) is not None
        )
        self._clear_entries()

        for entry in entries:
            self._append_entry(entry)

    def _clear_entries(self) -> None:
        self._entries_by_row.clear()
        self._hovered_row = None
        child = self.list_box.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            self.list_box.remove(child)
            child = next_child

    def _append_entry(self, entry: BrowserEntry) -> None:
        row = Gtk.ListBoxRow()
        row.add_css_class("folder-picker-row")

        content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        content.set_margin_top(5)
        content.set_margin_bottom(5)
        content.set_margin_start(10)
        content.set_margin_end(10)

        icon_name = (
            "folder-symbolic" if entry.is_directory else "text-x-generic-symbolic"
        )
        icon = Gtk.Image.new_from_icon_name(icon_name)
        content.append(icon)

        label = Gtk.Label(label=entry.name)
        label.set_halign(Gtk.Align.START)
        label.set_hexpand(True)
        label.set_ellipsize(3)
        content.append(label)

        row.set_child(content)
        self.list_box.append(row)
        self._entries_by_row[row] = entry

    def _navigate_up(self) -> None:
        parent = self._service.parent_directory(self._current_directory)
        if parent is not None:
            self._navigate(parent)

    def _on_pointer_motion(
        self, _controller: Gtk.EventControllerMotion, _x: float, y: float
    ) -> None:
        row = self.list_box.get_row_at_y(int(y))
        self._hovered_row = row if row in self._entries_by_row else None
        if self._hovered_row is not None:
            self.list_box.select_row(self._hovered_row)

    def _on_pointer_leave(self, _controller: Gtk.EventControllerMotion) -> None:
        self._hovered_row = None

    def _on_key_pressed(
        self,
        _controller: Gtk.EventControllerKey,
        keyval: int,
        _keycode: int,
        _state: Gdk.ModifierType,
    ) -> bool:
        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            row = self._hovered_row or self.list_box.get_selected_row()
            if row is not None:
                self._activate_row(row)
                return True
        elif keyval == Gdk.KEY_BackSpace:
            self._navigate_up()
            return True
        elif keyval == Gdk.KEY_Escape:
            self.close()
            return True
        return False

    def _on_row_activated(self, _list_box: Gtk.ListBox, row: Gtk.ListBoxRow) -> None:
        self._activate_row(row)

    def _activate_row(self, row: Gtk.ListBoxRow) -> None:
        entry = self._entries_by_row.get(row)
        if entry is None:
            return

        if entry.is_directory:
            self._navigate(entry.path)
            return

        try:
            self._on_file_opened(entry.path)
        except OSError as error:
            self.status.set_text(str(error))
            return
        self.close()

    def _open_current_folder(self) -> None:
        self._on_folder_opened(self._current_directory)
        self.close()
