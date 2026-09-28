from __future__ import annotations

import gi

gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, Gio, GObject

from ..menu_context import MenuContext


def is_enabled(context: MenuContext) -> bool:
    if context.editor_view is not None:
        return context.has_text_selection
    return context.path is not None


def run(context: MenuContext) -> None:
    if context.editor_view is not None:
        display = Gdk.Display.get_default()
        if display is not None and context.has_text_selection:
            context.editor_view.get_buffer().copy_clipboard(display.get_clipboard())
        return

    if context.path is not None:
        display = Gdk.Display.get_default()
        if display is not None:
            file_list = Gdk.FileList.new_from_array(
                [Gio.File.new_for_path(str(context.path.expanduser().resolve()))]
            )
            value = GObject.Value()
            value.init(Gdk.FileList.__gtype__)
            value.set_value(file_list)
            provider = Gdk.ContentProvider.new_for_value(value)
            display.get_clipboard().set_content(provider)