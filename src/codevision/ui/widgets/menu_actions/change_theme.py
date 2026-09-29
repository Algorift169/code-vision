from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from ..menu_context import MenuContext


def is_enabled(context: MenuContext) -> bool:
    return context.theme_manager is not None


def run(context: MenuContext) -> None:
    if context.theme_manager is None:
        return
    root = context.widget.get_root()
    parent = root if isinstance(root, Gtk.Window) else None
    context.theme_manager.show_dialog(parent)
