from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from .overlay_menu import OverlayMenuButton
from .symbolic_icon import create_symbolic_icon


class TerminalMenuButton(OverlayMenuButton):
    """Terminal menu for launching and controlling integrated sessions without Gtk.Popover."""

    def __init__(self, window: object, overlay: Gtk.Overlay | None = None) -> None:
        super().__init__(window, label="Terminal", overlay=overlay)
        self._build_items()

    def _make_row(
        self,
        label: str,
        callback: callable,
        *,
        shortcut: str = "",
        icon_name: str,
    ) -> Gtk.Button:
        button = Gtk.Button()
        button.set_has_frame(False)
        button.set_halign(Gtk.Align.FILL)
        button.add_css_class("context-menu-item")
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        row.set_hexpand(True)

        icon = create_symbolic_icon(icon_name, "terminal-menu-icon")
        row.append(icon)

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

    def _append_action(
        self,
        label: str,
        callback: callable,
        *,
        shortcut: str = "",
        icon_name: str,
    ) -> Gtk.Button:
        button = self._make_row(
            label, callback, shortcut=shortcut, icon_name=icon_name
        )
        self._content.append(button)
        return button

    def _build_items(self) -> None:
        self._append_action(
            "New Terminal", self._window.new_terminal,
            shortcut="Ctrl+Shift+`", icon_name="utilities-terminal-symbolic"
        )
        self._append_action(
            "Split Terminal", self._window.split_terminal,
            icon_name="view-split-left-right-symbolic"
        )
        self._content.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        self._append_action(
            "Run Active File", self._window.run_active_file,
            icon_name="media-playback-start-symbolic"
        )
        self._append_action(
            "Run Build", self._window.run_build, icon_name="system-run-symbolic"
        )
        self._content.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        self._append_action(
            "Clear Terminal", self._window.clear_terminal,
            icon_name="edit-clear-symbolic"
        )
        self._append_action(
            "Kill Terminal", self._window.kill_terminal,
            icon_name="process-stop-symbolic"
        )

    def update_state(self) -> None:
        editor_tabs = getattr(self._window, "editor_tabs", None)
        has_terminal = editor_tabs is not None and getattr(editor_tabs, "active_terminal", None) is not None
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
