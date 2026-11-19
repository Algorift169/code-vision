from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from codevision.ui.export.export_dialog import ExportDialog


class _Picker:
    def __init__(self) -> None:
        self.initial_directory = None
        self.callback = None

    def show_open_folder(self, initial_directory=None, on_folder_opened=None, **kwargs) -> None:
        self.initial_directory = initial_directory
        self.callback = on_folder_opened


class _Parent(Gtk.Window):
    def __init__(self) -> None:
        super().__init__(title="Test")
        self.file_picker = _Picker()


def test_export_dialog_uses_in_window_directory_picker(tmp_path):
    parent = _Parent()
    panel = Gtk.Box()
    dialog = ExportDialog(parent, panel, tmp_path)

    dialog.directory_entry.set_text(str(tmp_path))
    dialog._browse_directory(Gtk.Button())

    assert parent.file_picker.initial_directory == tmp_path
    assert callable(parent.file_picker.callback)

    assert dialog._set_output_directory(tmp_path / "reports") is False
    assert dialog.directory_entry.get_text() == str(tmp_path / "reports")
