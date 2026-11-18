from pathlib import Path

import gi
import pytest

gi.require_version("Gdk", "4.0")
gi.require_version("Gio", "2.0")
gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gio, Gtk

from codevision.ui.analysis_panel import AnalysisPanel
from space.importer import describe_file
from space.space_view import SpaceView


def test_importer_accepts_documents_and_unknown_file_types(tmp_path: Path) -> None:
    word_document = tmp_path / "notes.docx"
    unknown_file = tmp_path / "drawing.custom"
    word_document.write_bytes(b"document data")
    unknown_file.write_bytes(b"custom data")

    assert describe_file(word_document).path == word_document
    assert not describe_file(unknown_file).mime_type.startswith("video/")


def test_importer_rejects_video_files(tmp_path: Path) -> None:
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"not decoded based on extension")

    with pytest.raises(ValueError, match="Video files cannot be imported"):
        describe_file(video)


def test_space_imports_files_and_skips_videos(tmp_path: Path) -> None:
    document = tmp_path / "report.docx"
    video = tmp_path / "clip.webm"
    document.write_bytes(b"document")
    video.write_bytes(b"video")

    space = AnalysisPanel()._section_placeholders["Space"]
    imported = space.import_files(
        [document, video],
        position=(30.0, 40.0),
    )

    assert len(imported) == 1
    assert imported[0].path == document
    assert (imported[0].x, imported[0].y) == (30.0, 40.0)
    assert space.import_items == imported
    assert "clip.webm" in space.import_status.get_text()
    assert space.import_status.get_visible()


def test_imported_file_cards_move_smoothly_at_zoom(tmp_path: Path) -> None:
    document = tmp_path / "notes.docx"
    document.write_bytes(b"document")
    space = AnalysisPanel()._section_placeholders["Space"]
    item = space.import_files([document], (20.0, 30.0))[0]

    space.zoom.scale = 1.25
    item.apply_zoom()
    space._dragged_import_item = item
    space._import_drag_origin = (item.x, item.y)
    space._on_import_drag_update(None, 2.5, 1.5)

    assert (item.x, item.y) == (22.0, 31.2)
    transform = space.board.get_child_transform(item)
    assert transform is not None
    _, _, _, _, x, y = transform.to_2d()
    assert (x, y) == (27.5, 39.0)


def test_space_accepts_file_manager_drops_at_drop_position(
    tmp_path: Path,
) -> None:
    document = tmp_path / "report.docx"
    document.write_bytes(b"document")
    file_list = Gdk.FileList.new_from_array(
        [Gio.File.new_for_path(str(document))]
    )
    space = AnalysisPanel()._section_placeholders["Space"]

    assert space._on_files_dropped(None, file_list, 120.0, 80.0)
    assert len(space.import_items) == 1
    assert (space.import_items[0].x, space.import_items[0].y) == (120.0, 80.0)


def test_import_picker_uses_the_app_themed_gtk_dialog() -> None:
    window = Gtk.Window()
    space = SpaceView()
    window.set_child(space)

    space._on_import_clicked(None)
    dialog = space._import_dialog

    assert isinstance(dialog, Gtk.FileChooserDialog)
    assert "space-file-chooser" in dialog.get_css_classes()
    assert dialog.get_select_multiple()

    dialog.destroy()
    window.destroy()
