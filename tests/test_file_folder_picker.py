from pathlib import Path

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gtk

from codevision.app.main_window import CodeVisionWindow
from codevision.services.folder_browser import FolderBrowserService
from codevision.ui.project_explorer import ProjectExplorer
from codevision.ui.widgets.file_menu import FileMenuButton
from codevision.ui.widgets.folder import FolderPickerOverlay, FolderPickerWindow


def test_file_menu_has_both_open_file_and_open_folder() -> None:
    calls = []

    class DummyWindow:
        def __init__(self) -> None:
            self.content_overlay = Gtk.Overlay()
            self.editor_tabs = None

        def open_file_dialog(self) -> None:
            calls.append("open-file")

        def open_folder_dialog(self) -> None:
            calls.append("open-folder")

        def __getattr__(self, name: str):
            return lambda *args, **kwargs: None

    win = DummyWindow()
    menu = FileMenuButton(win, win.content_overlay)

    assert "open-file" in menu._items
    assert "open-folder" in menu._items

    # Trigger open-file button
    open_file_btn = menu._items["open-file"]
    open_file_btn.emit("clicked")
    assert calls == ["open-file"]

    # Trigger open-folder button
    open_folder_btn = menu._items["open-folder"]
    open_folder_btn.emit("clicked")
    assert calls == ["open-file", "open-folder"]


def test_folder_picker_opens_folder_and_navigates(tmp_path: Path) -> None:
    sub = tmp_path / "subdir"
    sub.mkdir()
    (sub / "file.txt").touch()

    opened_folders = []
    overlay = Gtk.Overlay()
    picker = FolderPickerOverlay(
        overlay=overlay,
        initial_directory=tmp_path,
        on_folder_opened=opened_folders.append,
        service=FolderBrowserService(),
        mode="folder",
    )
    picker.present()
    assert picker.get_visible()
    assert picker.get_active()

    # Navigate into subdir
    picker._navigate(sub)
    assert picker._current_directory == sub.resolve()

    # Confirm action in folder mode opens current directory
    picker._on_action_confirmed()
    assert opened_folders == [sub.resolve()]
    assert not picker.get_visible()


def test_folder_picker_file_mode_opens_file(tmp_path: Path) -> None:
    test_file = tmp_path / "hello.py"
    test_file.write_text("print('test')", encoding="utf-8")

    opened_files = []
    overlay = Gtk.Overlay()
    picker = FolderPickerOverlay(
        overlay=overlay,
        initial_directory=tmp_path,
        on_file_opened=opened_files.append,
        service=FolderBrowserService(),
        mode="file",
    )
    picker.present()

    # Find the row corresponding to test_file
    target_row = None
    for row, entry in picker._entries_by_row.items():
        if entry.path == test_file.resolve():
            target_row = row
            break

    assert target_row is not None
    picker.list_box.select_row(target_row)
    picker._on_action_confirmed()

    assert opened_files == [test_file.resolve()]
    assert not picker.get_visible()


def test_folder_picker_file_and_folder_icons_have_visible_styling(
    tmp_path: Path,
) -> None:
    (tmp_path / "folder").mkdir()
    (tmp_path / "file.txt").touch()
    picker = FolderPickerOverlay(
        overlay=Gtk.Overlay(),
        initial_directory=tmp_path,
        service=FolderBrowserService(),
        mode="file",
    )

    icons = {}
    for row in picker._entries_by_row:
        content = row.get_child()
        icon = content.get_first_child()
        icons[picker._entries_by_row[row].name] = icon

    assert icons["folder"].has_css_class("folder-picker-item-icon")
    assert icons["file.txt"].has_css_class("folder-picker-item-icon")
    assert all(
        icon.get_content_width() == 18
        and icon.get_content_height() == 18
        for icon in icons.values()
    )
    assert picker.up_button.get_child().has_css_class("folder-picker-control-icon")
    assert picker.up_button.get_child().get_content_width() == 18


def test_project_tree_uses_bundled_visible_file_and_folder_icons(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    folder = project / "folder"
    folder.mkdir(parents=True)
    file_path = project / "file.py"
    file_path.touch()

    explorer = ProjectExplorer(on_file_open=lambda _path: None)
    explorer._set_project_folder(project)
    root = explorer._store.get_iter_first()
    assert root is not None
    folder_iter = explorer._store.iter_nth_child(root, 0)
    file_iter = explorer._store.iter_nth_child(root, 1)

    folder_icon = explorer._store.get_value(folder_iter, 4)
    file_icon = explorer._store.get_value(file_iter, 4)
    assert folder_icon.get_width() == 18
    assert file_icon.get_width() == 18
    assert folder_icon is explorer._tree_icons["folder"]
    assert file_icon is explorer._tree_icons["file"]


def test_folder_picker_save_mode_saves_destination(tmp_path: Path) -> None:
    saved_files = []
    overlay = Gtk.Overlay()
    picker = FolderPickerOverlay(
        overlay=overlay,
        initial_directory=tmp_path,
        service=FolderBrowserService(),
        mode="save",
    )
    picker.show_save_file(
        title="Save Script",
        initial_directory=tmp_path,
        initial_filename="script.py",
        on_file_saved=saved_files.append,
    )
    assert picker.get_visible()
    assert picker.filename_entry.get_text() == "script.py"

    picker._on_action_confirmed()
    assert saved_files == [tmp_path / "script.py"]
    assert not picker.get_visible()


def test_folder_picker_keyboard_escape_closes() -> None:
    overlay = Gtk.Overlay()
    picker = FolderPickerOverlay(overlay=overlay)
    picker.present()
    assert picker.get_visible()

    handled = picker._on_key_pressed(
        None, Gdk.KEY_Escape, 0, Gdk.ModifierType(0)
    )
    assert handled
    assert not picker.get_visible()


def test_folder_picker_backward_compatible_close_request() -> None:
    closed = []
    overlay = Gtk.Overlay()
    picker = FolderPickerWindow(overlay=overlay)
    picker.connect("close-request", lambda p: closed.append(p))
    picker.present()
    assert picker.get_visible()

    picker.close()
    assert not picker.get_visible()
    assert closed == [picker]


def test_codevision_window_open_file_and_folder_dialogs_present_picker(tmp_path: Path) -> None:
    app = Gtk.Application(application_id="com.codevision.test")
    win = CodeVisionWindow(app)

    assert win.file_picker is not None
    assert not win.file_picker.get_visible()

    # Open File dialog
    win.open_file_dialog()
    assert win.file_picker.get_visible()
    assert win.file_picker._mode == "file"

    win.file_picker.close()
    assert not win.file_picker.get_visible()

    # Open Folder dialog
    win.open_folder_dialog()
    assert win.file_picker.get_visible()
    assert win.file_picker._mode == "folder"

    win.file_picker.close()
    assert not win.file_picker.get_visible()
