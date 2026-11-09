from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("GLib", "2.0")
gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, GLib, Gtk

from ...services.folder_browser import BrowserEntry, FolderBrowserService


class FolderPickerOverlay(Gtk.Box):
    """In-window file and folder browser overlay modal dialog.

    Operates as an overlay component attached directly to the window's
    Gtk.Overlay, avoiding external modal window management issues under Wayland
    and eliminating dependencies on external portal services.
    """

    def __init__(
        self,
        parent: Gtk.Window | Gtk.Widget | None = None,
        initial_directory: Path | None = None,
        on_folder_opened: Callable[[Path], None] | None = None,
        on_file_opened: Callable[[Path], None] | None = None,
        service: FolderBrowserService | None = None,
        *,
        overlay: Gtk.Overlay | None = None,
        mode: str = "folder",
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._parent = parent
        self._overlay: Gtk.Overlay | None = None
        self._close_handlers: list[tuple[Callable, tuple]] = []
        self._mode = mode  # "folder", "file", or "save"
        self._title = "Open Folder"
        self._service = service or FolderBrowserService()
        self._on_folder_opened = on_folder_opened
        self._on_file_opened = on_file_opened
        self._on_file_saved: Callable[[Path], None] | None = None

        if initial_directory is not None:
            expanded = initial_directory.expanduser()
            if not expanded.exists() or not expanded.is_dir():
                expanded = expanded.parent if expanded.parent.is_dir() else Path.home()
            self._current_directory = expanded
        else:
            self._current_directory = Path.home()

        self._entries_by_row: dict[Gtk.ListBoxRow, BrowserEntry] = {}
        self._hovered_row: Gtk.ListBoxRow | None = None

        self.set_hexpand(True)
        self.set_vexpand(True)
        self.set_halign(Gtk.Align.FILL)
        self.set_valign(Gtk.Align.FILL)
        self.add_css_class("folder-picker-backdrop")
        self.set_visible(False)

        # Centered dialog card container
        self.card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.card.set_halign(Gtk.Align.CENTER)
        self.card.set_valign(Gtk.Align.CENTER)
        self.card.set_size_request(680, 500)
        self.card.set_name("folder-picker-window")
        self.card.add_css_class("folder-picker-dialog")
        self.card.add_css_class("context-menu-popup")
        self.card.add_css_class("context-menu-content")
        self.card.add_css_class("codevision-context-menu")
        self.append(self.card)

        # Header
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header.add_css_class("folder-picker-headerbar")
        header.set_margin_top(8)
        header.set_margin_bottom(8)
        header.set_margin_start(12)
        header.set_margin_end(12)

        self.title_label = Gtk.Label(label="Open Folder")
        self.title_label.add_css_class("folder-picker-title")
        self.title_label.set_halign(Gtk.Align.START)
        self.title_label.set_hexpand(True)
        header.append(self.title_label)

        close_button = Gtk.Button()
        close_button.set_child(Gtk.Image.new_from_icon_name("window-close-symbolic"))
        close_button.add_css_class("folder-picker-icon-button")
        close_button.set_tooltip_text("Close")
        close_button.connect("clicked", lambda *_args: self.close())
        header.append(close_button)
        self.card.append(header)

        # Toolbar
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        toolbar.set_margin_top(10)
        toolbar.set_margin_bottom(10)
        toolbar.set_margin_start(12)
        toolbar.set_margin_end(12)
        toolbar.add_css_class("folder-picker-toolbar")

        self.heading = Gtk.Label(label="Browse folders")
        self.heading.set_halign(Gtk.Align.START)
        self.heading.add_css_class("folder-picker-heading")
        toolbar.append(self.heading)

        self.path_label = Gtk.Label()
        self.path_label.set_halign(Gtk.Align.START)
        self.path_label.set_hexpand(True)
        self.path_label.set_ellipsize(3)
        self.path_label.add_css_class("folder-picker-path")
        toolbar.append(self.path_label)

        self.show_hidden_toggle = Gtk.CheckButton(label="Show hidden files")
        self.show_hidden_toggle.add_css_class("folder-picker-hidden-toggle")
        self.show_hidden_toggle.connect("toggled", self._on_show_hidden_toggled)
        toolbar.append(self.show_hidden_toggle)

        self.up_button = Gtk.Button()
        self.up_button.set_child(Gtk.Image.new_from_icon_name("go-up-symbolic"))
        self.up_button.set_tooltip_text("Go to parent folder")
        self.up_button.add_css_class("folder-picker-icon-button")
        self.up_button.connect("clicked", lambda *_args: self._navigate_up())
        toolbar.append(self.up_button)
        self.card.append(toolbar)

        # List box and scrolling area
        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.list_box.set_activate_on_single_click(False)
        self.list_box.add_css_class("folder-picker-list")
        self.list_box.connect("row-activated", self._on_row_activated)
        self.list_box.connect("selected-rows-changed", self._on_selection_changed)

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
        self.card.append(scroller)

        # Save filename entry row (for save mode)
        self.save_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.save_row.set_margin_start(12)
        self.save_row.set_margin_end(12)
        self.save_row.set_margin_top(6)
        self.save_row.set_margin_bottom(6)
        self.save_row.set_visible(False)

        save_label = Gtk.Label(label="File name:")
        save_label.set_halign(Gtk.Align.START)
        self.save_row.append(save_label)

        self.filename_entry = Gtk.Entry()
        self.filename_entry.set_hexpand(True)
        self.filename_entry.set_activates_default(True)
        self.filename_entry.connect(
            "activate", lambda *_args: self._on_action_confirmed()
        )
        self.save_row.append(self.filename_entry)
        self.card.append(self.save_row)

        # Footer
        footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        footer.set_margin_top(10)
        footer.set_margin_bottom(12)
        footer.set_margin_start(12)
        footer.set_margin_end(12)

        self.status = Gtk.Label()
        self.status.set_halign(Gtk.Align.START)
        self.status.add_css_class("folder-picker-status")
        footer.append(self.status)

        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        footer.append(spacer)

        cancel_button = Gtk.Button(label="Cancel")
        cancel_button.connect("clicked", lambda *_args: self.close())
        footer.append(cancel_button)

        self.action_button = Gtk.Button(label="Open Folder")
        self.action_button.add_css_class("suggested-action")
        self.action_button.connect(
            "clicked", lambda *_args: self._on_action_confirmed()
        )
        footer.append(self.action_button)
        self.card.append(footer)

        # Keyboard controller for modal navigation
        key_controller = Gtk.EventControllerKey.new()
        key_controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        key_controller.connect("key-pressed", self._on_key_pressed)
        self.add_controller(key_controller)

        # Backdrop click dismiss controller
        dismiss_gesture = Gtk.GestureClick.new()
        dismiss_gesture.set_button(Gdk.BUTTON_PRIMARY)
        dismiss_gesture.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        dismiss_gesture.connect("pressed", self._on_backdrop_clicked)
        self.add_controller(dismiss_gesture)

        # Resolve overlay attachment
        resolved_overlay = overlay
        if resolved_overlay is None and parent is not None:
            if isinstance(parent, Gtk.Overlay):
                resolved_overlay = parent
            elif hasattr(parent, "content_overlay") and isinstance(
                parent.content_overlay, Gtk.Overlay
            ):
                resolved_overlay = parent.content_overlay
            elif hasattr(parent, "get_root"):
                root = parent.get_root()
                if hasattr(root, "content_overlay") and isinstance(
                    root.content_overlay, Gtk.Overlay
                ):
                    resolved_overlay = root.content_overlay

        if resolved_overlay is not None:
            self.set_overlay(resolved_overlay)

        self.set_mode(mode)
        self._navigate(self._current_directory)

    @property
    def dialog_card(self) -> Gtk.Box:
        return self.card

    def get_active(self) -> bool:
        return self.get_visible()

    def set_overlay(self, overlay: Gtk.Overlay) -> None:
        if self._overlay is not None and self.get_parent() is self._overlay:
            self._overlay.remove_overlay(self)
        self._overlay = overlay
        if overlay is not None and self.get_parent() is None:
            overlay.add_overlay(self)
            overlay.set_measure_overlay(self, False)

    def set_title(self, title: str) -> None:
        self._title = title
        self.title_label.set_text(title)

    def set_default_size(self, width: int, height: int) -> None:
        self.card.set_size_request(max(400, width), max(300, height))

    def set_size_request(self, width: int, height: int) -> None:
        self.card.set_size_request(max(400, width), max(300, height))

    def set_resizable(self, _resizable: bool) -> None:
        pass

    def set_modal(self, _modal: bool) -> None:
        pass

    def set_transient_for(self, _parent: Gtk.Window | None) -> None:
        pass

    def set_mode(self, mode: str) -> None:
        self._mode = mode
        if mode == "folder":
            self.set_title("Open Folder")
            self.heading.set_text("Browse folders")
            self.action_button.set_label("Open Folder")
            self.save_row.set_visible(False)
        elif mode == "file":
            self.set_title("Open File")
            self.heading.set_text("Browse files")
            self.action_button.set_label("Open File")
            self.save_row.set_visible(False)
        elif mode == "save":
            self.set_title(self._title or "Save File As")
            self.heading.set_text("Select save location")
            self.action_button.set_label("Save")
            self.save_row.set_visible(True)

    def show_open_folder(
        self,
        initial_directory: Path | None = None,
        on_folder_opened: Callable[[Path], None] | None = None,
        on_file_opened: Callable[[Path], None] | None = None,
    ) -> None:
        self.set_mode("folder")
        if on_folder_opened is not None:
            self._on_folder_opened = on_folder_opened
        if on_file_opened is not None:
            self._on_file_opened = on_file_opened
        if initial_directory is not None:
            expanded = initial_directory.expanduser()
            if not expanded.exists() or not expanded.is_dir():
                expanded = expanded.parent if expanded.parent.is_dir() else Path.home()
            self._current_directory = expanded
        self.present()

    def show_open_file(
        self,
        initial_directory: Path | None = None,
        on_file_opened: Callable[[Path], None] | None = None,
    ) -> None:
        self.set_mode("file")
        if on_file_opened is not None:
            self._on_file_opened = on_file_opened
        if initial_directory is not None:
            expanded = initial_directory.expanduser()
            if not expanded.exists() or not expanded.is_dir():
                expanded = expanded.parent if expanded.parent.is_dir() else Path.home()
            self._current_directory = expanded
        self.present()

    def show_save_file(
        self,
        title: str = "Save File As",
        initial_directory: Path | None = None,
        initial_filename: str = "",
        on_file_saved: Callable[[Path], None] | None = None,
    ) -> None:
        self.set_mode("save")
        self.set_title(title)
        self.filename_entry.set_text(initial_filename)
        if on_file_saved is not None:
            self._on_file_saved = on_file_saved
        if initial_directory is not None:
            expanded = initial_directory.expanduser()
            if not expanded.exists() or not expanded.is_dir():
                expanded = expanded.parent if expanded.parent.is_dir() else Path.home()
            self._current_directory = expanded
        self.present()

    def present(self) -> None:
        if self._overlay is None and self._parent is not None:
            if hasattr(self._parent, "content_overlay"):
                self.set_overlay(self._parent.content_overlay)
            elif hasattr(self._parent, "get_root"):
                root = self._parent.get_root()
                if hasattr(root, "content_overlay"):
                    self.set_overlay(root.content_overlay)

        if hasattr(self._parent, "close_all_menus"):
            self._parent.close_all_menus(except_menu=self)

        self.set_visible(True)
        self._navigate(self._current_directory)
        if self._mode == "save":
            self.filename_entry.grab_focus()
        else:
            self.list_box.grab_focus()

    def close(self) -> bool:
        if not self.get_visible():
            return False
        self.set_visible(False)
        for handler, args in list(self._close_handlers):
            try:
                handler(self, *args)
            except (RuntimeError, TypeError, ValueError, GLib.Error):
                pass
        return True

    def popdown(self) -> None:
        self.close()

    def connect(self, detailed_signal: str, handler: Callable, *args: object) -> int:
        if detailed_signal == "close-request":
            self._close_handlers.append((handler, args))
            return len(self._close_handlers)
        return super().connect(detailed_signal, handler, *args)

    def _on_backdrop_clicked(
        self, gesture: Gtk.GestureClick, _press_count: int, x: float, y: float
    ) -> None:
        if not self.get_visible():
            return
        ok, bounds = self.card.compute_bounds(self)
        if ok:
            bx = bounds.get_x()
            by = bounds.get_y()
            bw = bounds.get_width()
            bh = bounds.get_height()
            if bx <= x <= bx + bw and by <= y <= by + bh:
                gesture.set_state(Gtk.EventSequenceState.DENIED)
                return
        gesture.set_state(Gtk.EventSequenceState.CLAIMED)
        self.close()

    def _on_key_pressed(
        self,
        _controller: Gtk.EventControllerKey,
        keyval: int,
        _keycode: int,
        _state: Gdk.ModifierType,
    ) -> bool:
        if not self.get_visible():
            return False
        if keyval == Gdk.KEY_Escape:
            self.close()
            return True
        elif keyval == Gdk.KEY_BackSpace:
            if self._mode == "save" and self.filename_entry.is_focus():
                return False
            self._navigate_up()
            return True
        elif keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            if self._mode == "save" and self.filename_entry.is_focus():
                self._on_action_confirmed()
                return True
            row = self._hovered_row or self.list_box.get_selected_row()
            if row is not None:
                self._activate_row(row)
                return True
            self._on_action_confirmed()
            return True
        return False

    def _navigate(self, directory: Path) -> None:
        try:
            directory = directory.expanduser().resolve(strict=True)
            entries = self._service.list_entries(
                directory, show_hidden=self.show_hidden_toggle.get_active()
            )
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

    def _on_row_activated(self, _list_box: Gtk.ListBox, row: Gtk.ListBoxRow) -> None:
        self._activate_row(row)

    def _on_selection_changed(self, _list_box: Gtk.ListBox) -> None:
        selected_row = self.list_box.get_selected_row()
        entry = (
            self._entries_by_row.get(selected_row)
            if selected_row is not None
            else None
        )
        if self._mode == "save" and entry is not None and not entry.is_directory:
            self.filename_entry.set_text(entry.name)

    def _navigate_up(self) -> None:
        parent = self._service.parent_directory(self._current_directory)
        if parent is not None:
            self._navigate(parent)

    def _on_show_hidden_toggled(self, _button: Gtk.CheckButton) -> None:
        self._navigate(self._current_directory)

    def _on_pointer_motion(
        self, _controller: Gtk.EventControllerMotion, _x: float, y: float
    ) -> None:
        row = self.list_box.get_row_at_y(int(y))
        self._hovered_row = row if row in self._entries_by_row else None
        if self._hovered_row is not None:
            self.list_box.select_row(self._hovered_row)

    def _on_pointer_leave(self, _controller: Gtk.EventControllerMotion) -> None:
        self._hovered_row = None

    def _activate_row(self, row: Gtk.ListBoxRow) -> None:
        entry = self._entries_by_row.get(row)
        if entry is None:
            return

        if entry.is_directory:
            self._navigate(entry.path)
            return

        if not entry.path.is_file():
            self.status.set_text("This item is not a regular file")
            return

        if self._mode == "save":
            self.filename_entry.set_text(entry.name)
            return

        if self._on_file_opened is not None:
            try:
                self._on_file_opened(entry.path)
            except OSError as error:
                self.status.set_text(str(error))
                return
            self.close()

    def _on_action_confirmed(self) -> None:
        selected_row = self.list_box.get_selected_row()
        entry = (
            self._entries_by_row.get(selected_row)
            if selected_row is not None
            else None
        )

        if self._mode == "folder":
            if entry is not None and entry.is_directory:
                target = entry.path
            else:
                target = self._current_directory
            if self._on_folder_opened is not None:
                self._on_folder_opened(target)
            self.close()

        elif self._mode == "file":
            if entry is not None:
                if entry.is_directory:
                    self._navigate(entry.path)
                    return
                elif entry.path.is_file():
                    if self._on_file_opened is not None:
                        self._on_file_opened(entry.path)
                    self.close()
                    return
            self.status.set_text("Please select a file to open")

        elif self._mode == "save":
            name = self.filename_entry.get_text().strip()
            if not name or Path(name).name != name or name in {".", ".."}:
                self.status.set_text("Please enter a valid file name")
                return
            target = self._current_directory / name
            if self._on_file_saved is not None:
                self._on_file_saved(target)
            self.close()

    def _open_current_folder(self) -> None:
        self._on_action_confirmed()


# Backward-compatible alias
FolderPickerWindow = FolderPickerOverlay
