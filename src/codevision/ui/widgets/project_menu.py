from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from .overlay_menu import OverlayMenuButton


class ProjectMenuButton(OverlayMenuButton):
    """Project menu dropdown button for the menu bar."""

    def __init__(self, window: object, overlay: Gtk.Overlay | None = None) -> None:
        super().__init__(window, label="Project", overlay=overlay)
        menu_content = Gtk.Label(label="Project menu is not implemented yet")
        menu_content.set_margin_top(10)
        menu_content.set_margin_bottom(10)
        menu_content.set_margin_start(12)
        menu_content.set_margin_end(12)
        self._content.append(menu_content)


__all__ = ["ProjectMenuButton"]
