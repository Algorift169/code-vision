from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from .overlay_menu import OverlayMenuButton


class FileMenuButton(OverlayMenuButton):
    """File menu UI that delegates operations to its owning window without Gtk.Popover."""

    def __init__(self, window: object, overlay: Gtk.Overlay | None = None) -> None:
        super().__init__(window, label="File", overlay=overlay)
        self._items: dict[str, Gtk.Widget] = {}
        self._submenus: list[Gtk.Widget] = []
        self._build_items()

    def set_overlay(self, overlay: Gtk.Overlay) -> None:
        super().set_overlay(overlay)
        for sub in getattr(self, "_submenus", []):
            if sub.get_parent() is None and overlay is not None:
                overlay.add_overlay(sub)
                overlay.set_measure_overlay(sub, False)

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

    def _append_submenu(self, label: str) -> tuple[Gtk.Button, Gtk.Box]:
        button = Gtk.Button()
        button.set_halign(Gtk.Align.FILL)
        button.set_has_frame(False)
        button.add_css_class("context-menu-item")
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        title = Gtk.Label(label=label)
        title.set_halign(Gtk.Align.START)
        title.set_hexpand(True)
        arrow = Gtk.Label(label="▶")
        arrow.set_halign(Gtk.Align.END)
        arrow.add_css_class("muted-label")
        row.append(title)
        row.append(arrow)
        button.set_child(row)

        sub_popup = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        sub_popup.set_name("codevision-context-menu")
        sub_popup.add_css_class("context-menu-popup")
        sub_popup.add_css_class("context-menu-content")
        sub_popup.add_css_class("codevision-context-menu")
        sub_popup.set_halign(Gtk.Align.START)
        sub_popup.set_valign(Gtk.Align.START)
        sub_popup.set_visible(False)

        if self._overlay is not None:
            self._overlay.add_overlay(sub_popup)
            self._overlay.set_measure_overlay(sub_popup, False)

        self._submenus.append(sub_popup)

        def _on_submenu_toggle(_btn: Gtk.Button) -> None:
            if sub_popup.get_visible():
                sub_popup.set_visible(False)
            else:
                if self._overlay is None and hasattr(self._window, "content_overlay"):
                    self.set_overlay(getattr(self._window, "content_overlay"))
                if self._overlay is not None:
                    ok, rect = button.compute_bounds(self._overlay)
                    if ok:
                        sub_popup.set_margin_start(max(0, int(rect.get_x() + rect.get_width())))
                        sub_popup.set_margin_top(max(0, int(rect.get_y())))
                sub_popup.set_visible(True)

        button.connect("clicked", _on_submenu_toggle)
        self._content.append(button)
        return button, sub_popup

    def _close_submenus(self) -> None:
        for submenu in self._submenus:
            submenu.set_visible(False)

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

    def update_state(self) -> None:
        editor_tabs = getattr(self._window, "editor_tabs", None)
        has_editor = editor_tabs is not None and getattr(editor_tabs, "active_editor", None) is not None
        if "save" in self._items:
            self._items["save"].set_sensitive(has_editor)
        if "save-as" in self._items:
            self._items["save-as"].set_sensitive(has_editor)
        if "share" in self._items:
            self._items["share"].set_sensitive(has_editor)
        if "close-editor" in self._items:
            self._items["close-editor"].set_sensitive(has_editor)
        if hasattr(self, "_auto_save_on") and hasattr(self, "_auto_save_off"):
            on_label = self._auto_save_on.get_child()
            off_label = self._auto_save_off.get_child()
            enabled = getattr(self._window, "auto_save_enabled", False)
            if isinstance(on_label, Gtk.Label) and isinstance(off_label, Gtk.Label):
                on_label.set_text("✓ On" if enabled else "On")
                off_label.set_text("✓ Off" if not enabled else "Off")
