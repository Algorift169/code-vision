from __future__ import annotations

from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, Gtk


class TerminalMenuButton(Gtk.MenuButton):
    """Terminal menu for launching and controlling integrated sessions."""

    def __init__(self, window: object) -> None:
        super().__init__()
        self._window = window
        self.set_label("Terminal")
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

    def _make_row(self, label: str, callback: callable, *, shortcut: str = "") -> Gtk.Button:
        button = Gtk.Button()
        button.set_has_frame(False)
        button.set_halign(Gtk.Align.FILL)
        button.add_css_class("context-menu-item")
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        row.set_hexpand(True)

        title = Gtk.Label(label=label)
        title.set_halign(Gtk.Align.START)
        title.set_hexpand(True)
        title.set_xalign(0)
        row.append(title)

        if shortcut:
            shortcut_label = Gtk.Label(label=shortcut)
            shortcut_label.set_halign(Gtk.Align.END)
            shortcut_label.add_css_class("muted-label")
            row.append(shortcut_label)

        button.set_child(row)
        button.connect("clicked", lambda _button: (self.popdown(), callback()))
        return button

    def _append_action(self, label: str, callback: callable, *, shortcut: str = "") -> Gtk.Button:
        button = self._make_row(label, callback, shortcut=shortcut)
        self._content.append(button)
        return button

    def _build_items(self) -> None:
        self._append_action("New Terminal", self._window.new_terminal, shortcut="Ctrl+Shift+`")
        self._append_action("Split Terminal", self._window.split_terminal, shortcut="")
        self._content.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        self._append_action("Run Active File", self._window.run_active_file, shortcut="")
        self._append_action("Run Build", self._window.run_build, shortcut="")
        self._content.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        self._append_action("Clear Terminal", self._window.clear_terminal, shortcut="")
        self._append_action("Kill Terminal", self._window.kill_terminal, shortcut="")

    def update_state(self) -> None:
        has_terminal = self._window.editor_tabs.active_terminal is not None
        for child in self._content:
            if isinstance(child, Gtk.Button):
                child.set_sensitive(True)
        if not has_terminal:
            for child in self._content:
                if isinstance(child, Gtk.Button):
                    label = child.get_child()
                    if isinstance(label, Gtk.Box):
                        text_child = label.get_last_child()
                        if isinstance(text_child, Gtk.Label):
                            continue
                    child.set_sensitive(True)


__all__ = ["TerminalMenuButton"]
