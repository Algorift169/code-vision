from __future__ import annotations

import shutil
from pathlib import Path

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gio", "2.0")
from gi.repository import Gdk, Gio, GLib

from ..menu_context import MenuContext


def is_enabled(context: MenuContext) -> bool:
    if context.editor_view is not None:
        return context.editor_view.get_editable()
    if context.terminal_widget is not None:
        return True
    return context.kind in {"explorer", "window"} and context.directory.is_dir()


def run(context: MenuContext) -> None:
    if context.terminal_widget is not None:
        context.terminal_widget.paste_clipboard()
        return

    display = Gdk.Display.get_default()
    if display is None:
        return

    clipboard = display.get_clipboard()
    if context.editor_view is not None:
        context.editor_view.get_buffer().paste_clipboard(
            clipboard, None, context.editor_view.get_editable()
        )
        return

    def on_files_ready(clipboard: Gdk.Clipboard, result: Gio.AsyncResult) -> None:
        try:
            value = clipboard.read_value_finish(result)
            file_list = value.get_value()
            sources = [Path(file.get_path()) for file in file_list.get_files()]
            copied = copy_files_to_directory(sources, context.directory)
        except (GLib.Error, OSError, TypeError, ValueError) as error:
            if context.set_status is not None:
                context.set_status(str(error))
            return

        if context.on_files_pasted is not None:
            context.on_files_pasted(copied)

    clipboard.read_value_async(
        Gdk.FileList.__gtype__, GLib.PRIORITY_DEFAULT, None, on_files_ready
    )


def copy_files_to_directory(sources: list[Path], directory: Path) -> list[Path]:
    directory = directory.expanduser().resolve(strict=True)
    if not directory.is_dir():
        raise NotADirectoryError(directory)

    copied: list[Path] = []
    for source in sources:
        source = source.expanduser()
        if not source.exists():
            raise FileNotFoundError(source)
        destination = directory / source.name
        if destination.exists():
            raise FileExistsError(destination)
        if source.is_dir():
            shutil.copytree(source, destination)
        else:
            shutil.copy2(source, destination)
        copied.append(destination)
    return copied