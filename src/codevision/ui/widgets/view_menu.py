from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from .overlay_menu import OverlayMenuButton


class ViewMenuButton(OverlayMenuButton):
    """View menu for toggling panes, fullscreen, focus mode, zoom, and theme without Gtk.Popover."""

    def __init__(self, window: object, overlay: Gtk.Overlay | None = None) -> None:
        super().__init__(window, label="View", overlay=overlay)
        self._items: dict[str, Gtk.Button] = {}
        self._build_items()
        self._update_state()

    def _make_row(
        self,
        label: str,
        callback: callable,
        *,
        checked: bool = False,
        enabled: bool = True,
        shortcut: str = "",
    ) -> Gtk.Button:
        button = Gtk.Button()
        button.set_has_frame(False)
        button.set_halign(Gtk.Align.FILL)
        button.add_css_class("context-menu-item")
        button.set_sensitive(enabled)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        row.set_hexpand(True)

        check = Gtk.Label(label="✓" if checked else " ")
        check.set_halign(Gtk.Align.START)
        check.set_width_chars(2)
        row.append(check)

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
        checked: bool = False,
        enabled: bool = True,
        shortcut: str = "",
    ) -> Gtk.Button:
        button = self._make_row(
            label,
            callback,
            checked=checked,
            enabled=enabled,
            shortcut=shortcut,
        )
        self._content.append(button)
        return button

    def _build_items(self) -> None:
        self._items["editor"] = self._append_action(
            "Editor",
            self._window.toggle_editor_visibility,
            checked=self._window.editor_visible(),
        )
        self._items["project-explorer"] = self._append_action(
            "Project Explorer",
            self._window.toggle_project_explorer,
            checked=self._window.project_explorer_visible(),
        )
        self._items["analysis-panel"] = self._append_action(
            "Analysis Panel",
            self._window.toggle_analysis_panel,
            checked=self._window.analysis_panel_visible(),
        )
        self._content.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        self._items["fullscreen"] = self._append_action(
            "Toggle Full Screen",
            self._window._toggle_fullscreen,
            shortcut="F11",
        )
        self._items["focus-mode"] = self._append_action(
            "Focus Mode",
            self._window.toggle_focus_mode,
            checked=self._window.focus_mode_active(),
        )
        self._content.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        self._items["zoom-in"] = self._append_action(
            "Zoom In",
            self._window.zoom_in,
            shortcut="Ctrl++",
        )
        self._items["zoom-out"] = self._append_action(
            "Zoom Out",
            self._window.zoom_out,
            shortcut="Ctrl+-",
        )
        self._items["reset-zoom"] = self._append_action(
            "Reset Zoom",
            self._window.reset_zoom,
            shortcut="Ctrl+0",
        )
        self._content.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

    def update_state(self) -> None:
        self._update_state()

    def _update_state(self) -> None:
        if not hasattr(self._window, "editor_visible"):
            return
        for item_name in (
            "editor",
            "project-explorer",
            "analysis-panel",
            "fullscreen",
            "focus-mode",
            "zoom-in",
            "zoom-out",
            "reset-zoom",
        ):
            if item_name in self._items:
                self._items[item_name].set_sensitive(True)

        for item_name, item_widget in self._items.items():
            if item_name == "editor":
                self._update_checked(item_widget, self._window.editor_visible())
            elif item_name == "project-explorer":
                self._update_checked(item_widget, self._window.project_explorer_visible())
            elif item_name == "analysis-panel":
                self._update_checked(item_widget, self._window.analysis_panel_visible())
            elif item_name == "focus-mode":
                self._update_checked(item_widget, self._window.focus_mode_active())

    @staticmethod
    def _update_checked(button: Gtk.Button, checked: bool) -> None:
        row = button.get_child()
        if not isinstance(row, Gtk.Box):
            return
        check = row.get_first_child()
        if isinstance(check, Gtk.Label):
            check.set_text("✓" if checked else " ")


__all__ = ["ViewMenuButton"]
