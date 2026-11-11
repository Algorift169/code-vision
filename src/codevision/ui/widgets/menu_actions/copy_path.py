from __future__ import annotations

from pathlib import Path

import gi

gi.require_version("Gdk", "4.0")
from gi.repository import Gdk

from ....utils.gtk_text import gtk_safe_text
from ..menu_context import MenuContext


def path(context: MenuContext) -> Path | None:
    return context.path.expanduser().resolve() if context.path is not None else None


def is_enabled(context: MenuContext) -> bool:
    return path(context) is not None


def run(context: MenuContext) -> None:
    target = path(context)
    display = Gdk.Display.get_default()
    if target is not None and display is not None:
        display.get_clipboard().set(gtk_safe_text(str(target)))