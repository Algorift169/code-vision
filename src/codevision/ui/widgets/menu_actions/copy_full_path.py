from __future__ import annotations

from pathlib import Path

from gi.repository import Gdk

from ..menu_context import MenuContext


def full_path(context: MenuContext) -> Path | None:
    return context.path.expanduser().resolve() if context.path is not None else None


def is_enabled(context: MenuContext) -> bool:
    return full_path(context) is not None


def run(context: MenuContext) -> None:
    path = full_path(context)
    if path is None:
        return
    display = Gdk.Display.get_default()
    if display is not None:
        display.get_clipboard().set(str(path))