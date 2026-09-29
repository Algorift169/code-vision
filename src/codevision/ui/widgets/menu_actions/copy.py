from __future__ import annotations

import gi

gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, Gio, GObject

from ..menu_context import MenuContext


def file_list_provider(paths: tuple[Path, ...]) -> Gdk.ContentProvider:
    file_list = Gdk.FileList.new_from_array(
        [Gio.File.new_for_path(str(path.expanduser().resolve())) for path in paths]
    )
    value = GObject.Value()
    value.init(Gdk.FileList.__gtype__)
    value.set_value(file_list)
    return Gdk.ContentProvider.new_for_value(value)


def is_enabled(context: MenuContext) -> bool:
    if context.editor_view is not None:
        return context.has_text_selection
    if context.terminal_widget is not None:
        return context.terminal_widget.get_has_selection()
    return bool(context.selected_paths) or context.path is not None


def run(context: MenuContext) -> None:
    if context.editor_view is not None:
        display = Gdk.Display.get_default()
        if display is not None and context.has_text_selection:
            context.editor_view.get_buffer().copy_clipboard(display.get_clipboard())
        return

    if context.terminal_widget is not None:
        if context.terminal_widget.get_has_selection():
            context.terminal_widget.copy_clipboard()
        return

    paths = context.selected_paths or ((context.path,) if context.path is not None else ())
    if paths:
        display = Gdk.Display.get_default()
        if display is not None:
            display.get_clipboard().set_content(file_list_provider(paths))