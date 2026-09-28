from __future__ import annotations

from pathlib import Path

from gi.repository import Gdk

from ..menu_context import MenuContext


def relative_path(context: MenuContext) -> Path | None:
    if context.path is None or context.project_root is None:
        return None
    try:
        return context.path.resolve().relative_to(context.project_root.resolve())
    except ValueError:
        return None


def is_enabled(context: MenuContext) -> bool:
    return relative_path(context) is not None


def run(context: MenuContext) -> None:
    path = relative_path(context)
    if path is None:
        return
    display = Gdk.Display.get_default()
    if display is not None:
        display.get_clipboard().set(str(path))