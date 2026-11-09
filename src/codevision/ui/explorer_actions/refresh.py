from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from ..widgets.symbolic_icon import create_symbolic_icon


class RefreshAction(Gtk.Button):
    """Project Explorer button that reloads the current project tree."""

    def __init__(
        self,
        refresh: Callable[[], None],
    ) -> None:
        
        super().__init__()
        self._refresh = refresh
        icon = create_symbolic_icon("view-refresh-symbolic", "explorer-action-icon")
        self.set_child(icon)
        self.set_tooltip_text("Refresh")
        self.add_css_class("explorer-action")
        self.connect("clicked", lambda *_args: self.activate())

    def activate(self) -> None:
        self._refresh()