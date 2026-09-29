from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("GtkSource", "5")
from gi.repository import Gtk, GtkSource

from ...services.terminal import TerminalService
from ..theme import ThemeManager


@dataclass(slots=True)
class MenuContext:
    widget: Gtk.Widget
    kind: str
    path: Path | None = None
    selected_paths: tuple[Path, ...] = ()
    project_root: Path | None = None
    tree: Gtk.TreeView | None = None
    editor_view: GtkSource.View | None = None
    terminal_widget: Gtk.Widget | None = None
    terminal_service: TerminalService | None = None
    theme_manager: ThemeManager | None = None
    open_terminal: Callable[[], None] | None = None
    create_file: Callable[[], None] | None = None
    on_files_pasted: Callable[[list[Path]], None] | None = None
    on_path_deleted: Callable[[Path], None] | None = None
    on_path_renamed: Callable[[Path, Path], None] | None = None
    select_target: Callable[[], None] | None = None
    set_status: Callable[[str], None] | None = None

    @property
    def directory(self) -> Path:
        if self.path is not None:
            return self.path if self.path.is_dir() else self.path.parent
        if self.project_root is not None:
            return self.project_root
        return Path.cwd()

    @property
    def has_text_selection(self) -> bool:
        if self.editor_view is None:
            return False
        bounds = self.editor_view.get_buffer().get_selection_bounds()
        return bool(bounds) and not bounds[0].equal(bounds[1])
