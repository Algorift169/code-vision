from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk


class CollapseAllAction(Gtk.Button):
    """Project Explorer button that collapses every expanded directory."""

    def __init__(
        self,
        collapse_all: Callable[[], None],
    ) -> None:
        super().__init__()
        self._collapse_all = collapse_all
        self.set_child(Gtk.Image.new_from_icon_name("view-list-symbolic"))
        self.set_tooltip_text("Collapse All")
        self.add_css_class("explorer-action")
        self.connect("clicked", lambda *_args: self.activate())

    def activate(self) -> None:
        self._collapse_all()