from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from .overlay_menu import OverlayMenuButton


class ProjectMenuButton(OverlayMenuButton):
    """Project menu dropdown button for the menu bar."""

    def __init__(self, window: object, overlay: Gtk.Overlay | None = None) -> None:
        super().__init__(window, label="Project", overlay=overlay)
        self._items: dict[str, Gtk.Button] = {}
        self._items["vision"] = self._append_action(
            "Vision", self._window.show_analysis_panel
        )

    def _append_action(
        self, label: str, callback: Callable[[], None]
    ) -> Gtk.Button:
        button = Gtk.Button(label=label)
        button.set_has_frame(False)
        button.set_halign(Gtk.Align.FILL)
        button.add_css_class("context-menu-item")

        def on_clicked(_button: Gtk.Button) -> None:
            self.popdown()
            callback()

        button.connect("clicked", on_clicked)
        self._content.append(button)
        return button


__all__ = ["ProjectMenuButton"]
