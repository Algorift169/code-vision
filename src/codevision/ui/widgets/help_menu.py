from __future__ import annotations

from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, Gtk


class HelpMenuButton(Gtk.MenuButton):
    """Help menu with documentation, shortcuts, and about info."""

    def __init__(self, window: object) -> None:
        super().__init__()
        self._window = window
        self.set_label("Help")
        self.add_css_class("menu-button")

        self._popover = Gtk.Popover()
        self._popover.set_name("codevision-context-menu")
        self._popover.set_has_arrow(False)
        self._popover.set_autohide(True)
        self._popover.add_css_class("codevision-context-menu")

        self._content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        self._content.add_css_class("context-menu-content")
        self._popover.set_child(self._content)
        self.set_popover(self._popover)

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
