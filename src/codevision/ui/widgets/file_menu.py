from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk


class FileMenuButton(Gtk.MenuButton):
    """File menu UI that delegates operations to its owning window."""

    def __init__(self, window: object) -> None:
        super().__init__()
        self._window = window
        self.set_label("File")
        self.add_css_class("menu-button")

        self._popover = self._create_popover()
        self._content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        self._content.add_css_class("context-menu-content")
        self._popover.set_child(self._content)
        self.set_popover(self._popover)
        self.connect("notify::active", self._on_menu_active_changed)
        self._items: dict[str, Gtk.Widget] = {}
        self._build_items()

    def _create_popover(self) -> Gtk.Popover:
        popover = Gtk.Popover()
        popover.set_name("codevision-context-menu")
        popover.set_has_arrow(False)
        popover.set_autohide(True)
        popover.add_css_class("codevision-context-menu")
        return popover

    def _build_items(self) -> None:
        self._items["new-file"] = self._append_action("New File", self._window.new_file)
        self._items["new-text-file"] = self._append_action(
            "New Text File", self._window.new_text_file
        )
        self._items["new-window"] = self._append_action(
            "New Window", self._window.new_window
        )
        self._items["open-file"] = self._append_action(
            "Open File...", self._window.open_file_dialog
        )

        self._recent_button, self._recent_box = self._append_submenu("Open Recent")
        self._content.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        self._items["save"] = self._append_action("Save", self._window.save_current_file)
        self._items["save-as"] = self._append_action(
            "Save As...", self._window.save_file_as
        )
        self._content.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        self._items["share"] = self._append_action(
            "Share", self._window.share_current_file
        )

        self._auto_save_button, auto_box = self._append_submenu("Auto Save")
        self._auto_save_on = self._make_button(
            "On", lambda: self._window.set_auto_save(True)
        )
        self._auto_save_off = self._make_button(
            "Off", lambda: self._window.set_auto_save(False)
        )
        auto_box.append(self._auto_save_on)
        auto_box.append(self._auto_save_off)

        self._content.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        self._items["close-editor"] = self._append_action(
            "Close Editor", self._window.close_active_editor
        )

    def _append_action(self, label: str, callback: Callable[[], None]) -> Gtk.Button:
        button = self._make_button(label, callback)
        self._content.append(button)
        return button

    def _append_submenu(self, label: str) -> tuple[Gtk.MenuButton, Gtk.Box]:
        button = Gtk.MenuButton(label=label)
        button.set_halign(Gtk.Align.FILL)
        button.set_has_frame(False)
        button.add_css_class("context-menu-item")
        popover = self._create_popover()
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        content.add_css_class("context-menu-content")
        popover.set_child(content)
        button.set_popover(popover)
        self._content.append(button)
        return button, content

    def _make_button(self, label: str, callback: Callable[[], None]) -> Gtk.Button:
        button = Gtk.Button()
        button.set_has_frame(False)
        button.set_halign(Gtk.Align.FILL)
        button.add_css_class("context-menu-item")
        title = Gtk.Label(label=label)
        title.set_halign(Gtk.Align.START)
        button.set_child(title)
        button.connect("clicked", lambda _button: (self.popdown(), callback()))
        return button

    def _on_menu_active_changed(self, *_args: object) -> None:
        if self.get_active():
            self.update_recent(self._window.recent_files.get_recent())
            self.update_state()

    def update_recent(self, recent_paths: list[Path]) -> None:
        child = self._recent_box.get_first_child()
        while child is not None:
            following = child.get_next_sibling()
            self._recent_box.remove(child)
            child = following

        if not recent_paths:
            self._recent_button.set_sensitive(False)
            empty = Gtk.Label(label="No recent files")
            empty.add_css_class("muted-label")
            empty.set_margin_top(6)
            empty.set_margin_bottom(6)
            empty.set_margin_start(8)
            empty.set_margin_end(8)
            self._recent_box.append(empty)
            return

        self._recent_button.set_sensitive(True)
        for path in recent_paths:
            button = self._make_button(
                path.name,
                lambda recent_path=path: self._window.open_recent_file(recent_path),
            )
            button.set_tooltip_text(str(path))
            self._recent_box.append(button)

    def update_state(self) -> None:
        has_editor = self._window.editor_tabs.active_editor is not None
        self._items["save"].set_sensitive(has_editor)
        self._items["save-as"].set_sensitive(has_editor)
        self._items["share"].set_sensitive(has_editor)
        self._items["close-editor"].set_sensitive(has_editor)
        on_label = self._auto_save_on.get_child()
        off_label = self._auto_save_off.get_child()
        if isinstance(on_label, Gtk.Label) and isinstance(off_label, Gtk.Label):
            on_label.set_text("✓ On" if self._window.auto_save_enabled else "On")
            off_label.set_text("✓ Off" if not self._window.auto_save_enabled else "Off")
