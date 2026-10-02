from types import SimpleNamespace

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("GtkSource", "5")
from gi.repository import Gtk, GtkSource

from codevision.editor.editor import EditorPanel
from codevision.ui.widgets.edit_menu import EditMenuButton


class FakeButton:
    def __init__(self) -> None:
        self.sensitive = True

    def set_sensitive(self, value: bool) -> None:
        self.sensitive = value


class FakeBuffer:
    def __init__(self, can_undo: bool = False, can_redo: bool = False) -> None:
        self._can_undo = can_undo
        self._can_redo = can_redo

    def get_can_undo(self) -> bool:
        return self._can_undo

    def get_can_redo(self) -> bool:
        return self._can_redo

    def get_selection_bounds(self):
        return (SimpleNamespace(equal=lambda other: True), SimpleNamespace(equal=lambda other: True))


class FakeEditor:
    def __init__(self, buffer: FakeBuffer | None = None) -> None:
        self.buffer = buffer or FakeBuffer()
        self.source_view = SimpleNamespace(get_editable=lambda: True)
        self.file_path = None
        self.title = SimpleNamespace(get_text=lambda: "untitled")


class FakeEditorTabs:
    def __init__(self, editor: FakeEditor | None) -> None:
        self._editor = editor

    @property
    def active_editor(self) -> FakeEditor | None:
        return self._editor


class FakeWindow:
    def __init__(self, editor: FakeEditor | None) -> None:
        self.editor_tabs = FakeEditorTabs(editor)

    def undo(self) -> None:
        pass

    def redo(self) -> None:
        pass

    def cut(self) -> None:
        pass

    def copy(self) -> None:
        pass

    def paste(self) -> None:
        pass

    def find(self) -> None:
        pass

    def replace(self) -> None:
        pass

    def find_in_files(self) -> None:
        pass

    def replace_in_files(self) -> None:
        pass

    def toggle_line_comment(self) -> None:
        pass

    def toggle_block_comment(self) -> None:
        pass

    def expand_abbreviation(self) -> None:
        pass


def test_edit_menu_button_tracks_active_editor_state() -> None:
    window = FakeWindow(None)
    menu = EditMenuButton.__new__(EditMenuButton)
    menu._window = window
    menu._items = {
        key: FakeButton()
        for key in (
            "undo",
            "redo",
            "cut",
            "copy",
            "paste",
            "find",
            "replace",
            "find-in-files",
            "replace-in-files",
            "toggle-line-comment",
            "toggle-block-comment",
            "expand-abbreviation",
        )
    }

    menu.update_state()
    assert menu._items["undo"].sensitive is False
    assert menu._items["redo"].sensitive is False

    editor = FakeEditor(FakeBuffer())
    window.editor_tabs = FakeEditorTabs(editor)
    menu.update_state()
    assert menu._items["undo"].sensitive is False
    assert menu._items["redo"].sensitive is False
    assert menu._items["cut"].sensitive is False
    assert menu._items["copy"].sensitive is False
    assert menu._items["paste"].sensitive is True


def test_editor_toggle_line_comment_uses_textiter_objects() -> None:
    Gtk.init()
    editor = EditorPanel.__new__(EditorPanel)
    editor.buffer = GtkSource.Buffer()
    editor.source_view = SimpleNamespace(get_editable=lambda: True)
    buffer = editor.buffer
    buffer.set_text("print('hello')\n")

    buffer.place_cursor(buffer.get_start_iter())

    editor.toggle_line_comment()

    result = buffer.get_text(*buffer.get_bounds(), True)
    assert result == "#print('hello')\n"

    editor_2 = EditorPanel.__new__(EditorPanel)
    editor_2.buffer = GtkSource.Buffer()
    editor_2.source_view = SimpleNamespace(get_editable=lambda: True)
    editor_2.buffer.set_text("div>p*2")
    editor_2.buffer.place_cursor(editor_2.buffer.get_end_iter())
    assert editor_2.expand_abbreviation() is True
