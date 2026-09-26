from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk


class WindowBorder(Gtk.Box):
    """Thin custom frame around the app content, without a top border."""

    def __init__(self, child: Gtk.Widget) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.add_css_class("window-border")
        self.set_hexpand(True)
        self.set_vexpand(True)
        child.set_hexpand(True)
        child.set_vexpand(True)
        self.append(child)