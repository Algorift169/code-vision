from pathlib import Path

import gi
import pytest

gi.require_version("Gdk", "4.0")
gi.require_version("Gio", "2.0")
gi.require_version("Gtk", "4.0")
gi.require_version("Pango", "1.0")
from gi.repository import Gdk, Gio, Gtk, Pango

from codevision.ui.analysis_panel import AnalysisPanel
from codevision.space.importer import describe_file
from codevision.space.space_view import SpaceView


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


def test_imported_files_do_not_block_space_drawing_or_text(tmp_path: Path) -> None:
    document = tmp_path / "long-imported-filename-document.docx"
    document.write_bytes(b"document")
    space = AnalysisPanel()._section_placeholders["Space"]
    space._set_canvas_extent("width", 500)
    space._set_canvas_extent("height", 500)
    item = space.import_files([document], (20.0, 30.0))[0]

    assert space.board.get_last_child() is space.ink_canvas
    assert space.pen.canvas is space.ink_canvas
    requested_width, requested_height = item.get_size_request()
    assert requested_width < 184
    assert requested_height < 132
    attributes = item.filename_label.get_attributes()
    assert attributes is not None
    assert f"size {8 * Pango.SCALE}" in attributes.to_string()
    assert item.preview.get_pixel_size() == 32

    space.duplicate_board_item(item)
    assert space.board.get_last_child() is space.ink_canvas

    space.tool_buttons["Pen"].set_active(True)
    assert space.ink_canvas.get_can_target()
    space.pen._on_drag_begin(None, 30.0, 40.0)
    space.pen._on_drag_end(None, 20.0, 0.0)
    assert space.pen.strokes

    space.tool_buttons["Pen"].set_active(False)
    space.tool_buttons["Text Box"].set_active(True)
    assert space.ink_canvas.get_can_target()
    space._on_canvas_pressed(None, 1, 25.0, 35.0)
    assert (space.text_boxes[-1].x, space.text_boxes[-1].y) == (25.0, 35.0)
    assert not space.ink_canvas.get_can_target()


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
    action_buttons = []
    pending = [dialog]
    while pending:
        widget = pending.pop()
        if isinstance(widget, Gtk.Button) and (
            "space-import-action" in widget.get_css_classes()
        ):
            action_buttons.append(widget)
        child = widget.get_first_child()
        while child is not None:
            pending.append(child)
            child = child.get_next_sibling()
    assert len(action_buttons) == 2
    assert any(
        "suggested-action" in button.get_css_classes()
        for button in action_buttons
    )

    dialog.destroy()
    window.destroy()
