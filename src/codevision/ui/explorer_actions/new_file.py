from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from ..widgets.menu_context import MenuContext
from ..widgets.symbolic_icon import create_symbolic_icon


class NewFileAction(Gtk.Button):
    """Project Explorer button that creates and opens a new file."""

    def __init__(
        self,
        get_directory: Callable[[], Path],
        on_created: Callable[[Path], None],
    ) -> None:
        super().__init__()
        self._get_directory = get_directory
        self._on_created = on_created
        self._open_action_menu: (
            Callable[[str, MenuContext, Gtk.Widget], None] | None
        ) = None

        icon = create_symbolic_icon("document-new-symbolic", "explorer-action-icon")
        self.set_child(icon)
        self.set_tooltip_text("New File")
        self.add_css_class("explorer-action")
        self.set_sensitive(False)
        self.connect("clicked", lambda *_args: self.activate())

    def set_action_menu(
        self, callback: Callable[[str, MenuContext, Gtk.Widget], None]
    ) -> None:
        self._open_action_menu = callback
        self.set_sensitive(True)

    def activate(self) -> None:
        self.activate_in(self._get_directory())

    def activate_in(self, directory: Path) -> None:
        if self._open_action_menu is None:
            raise RuntimeError("The inline New File menu is not configured")
        context = MenuContext(
            widget=self,
            kind="explorer",
            path=directory,
            project_root=directory,
            on_path_created=self._on_created,
        )
        self._open_action_menu("new-file", context, self)