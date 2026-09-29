from pathlib import Path

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("GtkSource", "5")
from gi.repository import Gdk, GtkSource

from codevision.ui.widgets.menu_actions.copy_full_path import full_path
from codevision.ui.widgets.menu_actions.copy_relative_path import relative_path
from codevision.ui.widgets.menu_actions import copy, paste
from codevision.ui.widgets.menu_actions.paste import copy_files_to_directory
from codevision.ui.widgets.menu_actions import select, select_all
from codevision.ui.widgets.menu_context import MenuContext


class SelectionWidget:
    def __init__(self) -> None:
        self.focused = False
        self.all_selected = False
        self.has_selection = True
        self.copy_count = 0
        self.paste_count = 0

    def grab_focus(self) -> None:
        self.focused = True

    def select_all(self) -> None:
        self.all_selected = True

    def get_has_selection(self) -> bool:
        return self.has_selection

    def copy_clipboard(self) -> None:
        self.copy_count += 1

    def paste_clipboard(self) -> None:
        self.paste_count += 1


class EditorBufferView:
    def __init__(self, buffer: GtkSource.Buffer) -> None:
        self._buffer = buffer

    def get_buffer(self) -> GtkSource.Buffer:
        return self._buffer

    def get_editable(self) -> bool:
        return True


def test_path_copy_actions_resolve_paths_with_spaces(tmp_path: Path) -> None:
    root = tmp_path / "project with spaces"
    file_path = root / "source files" / "main file.py"
    file_path.parent.mkdir(parents=True)
    file_path.touch()
    context = MenuContext(
        widget=None,
        kind="explorer",
        path=file_path,
        project_root=root,
    )

    assert full_path(context) == file_path.resolve()
    assert relative_path(context) == Path("source files/main file.py")


def test_relative_path_rejects_paths_outside_project(tmp_path: Path) -> None:
    root = tmp_path / "project"
    outside = tmp_path / "outside.py"
    root.mkdir()
    outside.touch()
    context = MenuContext(
        widget=None,
        kind="explorer",
        path=outside,
        project_root=root,
    )

    assert relative_path(context) is None


def test_file_paste_copies_files_and_directories_with_spaces(tmp_path: Path) -> None:
    source_root = tmp_path / "source files"
    source_root.mkdir()
    source_file = source_root / "main file.py"
    source_file.write_text("print('hello')", encoding="utf-8")
    source_folder = source_root / "folder with spaces"
    source_folder.mkdir()
    (source_folder / "nested.txt").write_text("nested", encoding="utf-8")
    destination = tmp_path / "destination"
    destination.mkdir()

    copied = copy_files_to_directory([source_file, source_folder], destination)

    assert copied == [destination / source_file.name, destination / source_folder.name]
    assert copied[0].read_text(encoding="utf-8") == "print('hello')"
    assert (copied[1] / "nested.txt").read_text(encoding="utf-8") == "nested"


def test_select_actions_are_enabled_and_work_in_terminal_context() -> None:
    terminal = SelectionWidget()
    context = MenuContext(
        widget=terminal,
        kind="terminal",
        terminal_widget=terminal,
    )

    assert select.is_enabled(context)
    assert select_all.is_enabled(context)
    select.run(context)
    select_all.run(context)
    assert terminal.focused
    assert terminal.all_selected


def test_select_actions_remain_enabled_in_generic_context() -> None:
    widget = SelectionWidget()
    context = MenuContext(widget=widget, kind="window")

    assert select.is_enabled(context)
    assert select_all.is_enabled(context)
    select.run(context)
    select_all.run(context)
    assert widget.focused


def test_terminal_copy_and_paste_use_native_clipboard_actions() -> None:
    terminal = SelectionWidget()
    context = MenuContext(
        widget=terminal,
        kind="terminal",
        terminal_widget=terminal,
    )

    assert copy.is_enabled(context)
    assert paste.is_enabled(context)
    copy.run(context)
    paste.run(context)
    assert terminal.copy_count == 1
    assert terminal.paste_count == 1


def test_terminal_copy_requires_a_text_selection() -> None:
    terminal = SelectionWidget()
    terminal.has_selection = False
    context = MenuContext(
        widget=terminal,
        kind="terminal",
        terminal_widget=terminal,
    )

    assert not copy.is_enabled(context)
    copy.run(context)
    assert terminal.copy_count == 0


def test_editor_copy_and_paste_available_after_select_all() -> None:
    buffer = GtkSource.Buffer()
    buffer.set_text("selected editor text")
    editor_view = EditorBufferView(buffer)
    context = MenuContext(
        widget=editor_view,
        kind="editor",
        editor_view=editor_view,
    )

    select_all.run(context)

    assert context.has_text_selection
    assert copy.is_enabled(context)
    assert paste.is_enabled(context)


def test_explorer_copy_enabled_for_multiple_selected_paths(tmp_path: Path) -> None:
    paths = (tmp_path / "first file.txt", tmp_path / "second file.txt")
    context = MenuContext(
        widget=None,
        kind="explorer",
        selected_paths=paths,
    )

    assert copy.is_enabled(context)
    provider = copy.file_list_provider(paths)
    assert provider.ref_formats().contain_gtype(Gdk.FileList.__gtype__)
