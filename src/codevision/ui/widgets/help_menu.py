from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from .overlay_menu import OverlayMenuButton


class HelpMenuButton(OverlayMenuButton):
    """Help menu with documentation, shortcuts, and about info without Gtk.Popover."""

    def __init__(self, window: object, overlay: Gtk.Overlay | None = None) -> None:
        super().__init__(window, label="Help", overlay=overlay)
        self._build_items()

    def _make_row(self, label: str, callback: callable) -> Gtk.Button:
        button = Gtk.Button()
        button.set_has_frame(False)
        button.set_halign(Gtk.Align.FILL)
        button.add_css_class("context-menu-item")
        title = Gtk.Label(label=label)
        title.set_halign(Gtk.Align.START)
        title.set_hexpand(True)
        title.set_xalign(0)
        button.set_child(title)
        button.connect("clicked", lambda _button: (self.popdown(), callback()))
        return button

    def _append_action(self, label: str, callback: callable) -> Gtk.Button:
        button = self._make_row(label, callback)
        self._content.append(button)
        return button

    def _build_items(self) -> None:
        self._append_action("Documentation", self._window.open_documentation)
        self._append_action("Keyboard Shortcuts", self._window.show_shortcuts_dialog)
        self._append_action("CodeVision Guide", self._window.show_guide_dialog)
        self._content.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        self._append_action("Report an Issue", self._window.report_issue)
        self._append_action("View Source Code", self._window.view_source_code)
        self._append_action("Check for Updates", self._window.check_for_updates)
        self._content.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        self._append_action("About CodeVision", self._window.show_about_dialog)


__all__ = ["HelpMenuButton"]
