from __future__ import annotations

import shutil
from pathlib import Path

import gi

gi.require_version("Gdk", "4.0")
from gi.repository import Gdk

from ..menu_context import MenuContext

_CUT_PATHS: tuple[Path, ...] = ()


def is_enabled(context: MenuContext) -> bool:
    path = context.path
    if context.kind != "explorer" or path is None or not path.exists():
        return False
    if context.project_root is None:
        return False
    try:
        return path.resolve() != context.project_root.resolve() and path.resolve().is_relative_to(
            context.project_root.resolve()
        )
    except (OSError, ValueError):
        return False


def run(context: MenuContext) -> None:
    global _CUT_PATHS
    if not is_enabled(context) or context.path is None:
        return
    display = Gdk.Display.get_default()
    if display is None:
        return
    from .copy import file_list_provider

    paths = (context.path,)
    display.get_clipboard().set_content(file_list_provider(paths))
    _CUT_PATHS = paths
    if context.set_status is not None:
        context.set_status(f"Cut: {context.path.name}")


def is_cut_selection(paths: list[Path]) -> bool:
    return bool(_CUT_PATHS) and tuple(paths) == _CUT_PATHS


def clear_cut_selection() -> None:
    global _CUT_PATHS
    _CUT_PATHS = ()


def move_files_to_directory(sources: list[Path], directory: Path) -> list[Path]:
    directory = directory.expanduser().resolve(strict=True)
    if not directory.is_dir():
        raise NotADirectoryError(directory)

    destinations: list[tuple[Path, Path]] = []
    for source in sources:
        source = source.expanduser()
        if not source.exists() and not source.is_symlink():
            raise FileNotFoundError(source)
        source_resolved = source.resolve()
        if source.is_dir() and directory.is_relative_to(source_resolved):
            raise ValueError("A folder cannot be moved into itself")
        destination = directory / source.name
        if destination.exists() or destination.is_symlink():
            raise FileExistsError(destination)
        destinations.append((source, destination))

    moved: list[Path] = []
    for source, destination in destinations:
        shutil.move(str(source), str(destination))
        moved.append(destination)
    return moved