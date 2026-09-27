from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk


class AnalysisPanel(Gtk.Box):
    """Right-hand analysis dashboard panel with static overview placeholders."""

    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_name("analysis-panel")
        self.add_css_class("panel")
        self.set_vexpand(True)
        self.set_hexpand(True)
        self.set_size_request(184, -1)
        self.set_margin_top(0)
        self.set_margin_bottom(0)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header.set_margin_top(10)
        header.set_margin_bottom(8)
        header.set_margin_start(12)
        header.set_margin_end(12)
        header.add_css_class("panel-header")

        title = Gtk.Label(label="Analysis")
        title.add_css_class("section-title")
        title.set_halign(Gtk.Align.START)
        header.append(title)
        self.append(header)
