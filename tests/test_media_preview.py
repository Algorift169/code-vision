import base64
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")

from codevision.editor.editor import EditorPanel
from codevision.editor.image_preview import ImagePreview
from codevision.editor.tab import EditorTabs
from codevision.editor.video_preview import VideoPreview

_ONE_PIXEL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGP4z8DwHwAFAAH/iZk9HQAAAABJRU5ErkJggg=="
)


def test_open_image_in_its_own_reusable_editor_tab(tmp_path: Path) -> None:
    image_path = tmp_path / "preview.png"
    image_path.write_bytes(_ONE_PIXEL_PNG)
    tabs = EditorTabs()

    preview = tabs.open_file(image_path)

    assert isinstance(preview, ImagePreview)
    assert preview.file_path == image_path.resolve()
    assert preview.picture.get_paintable() is not None
    assert tabs.active_preview is preview
    assert tabs.open_file(image_path) is preview
    assert tabs.get_n_pages() == 1


def test_open_video_in_its_own_reusable_editor_tab(tmp_path: Path) -> None:
    video_path = tmp_path / "clip.mp4"
    video_path.touch()
    tabs = EditorTabs()

    preview = tabs.open_file(video_path)

    assert isinstance(preview, VideoPreview)
    assert preview.file_path == video_path.resolve()
    assert preview.video.get_file().get_path() == str(video_path.resolve())
    assert tabs.active_preview is preview
    assert tabs.open_file(video_path) is preview
    assert tabs.get_n_pages() == 1


def test_text_files_still_open_in_source_editor(tmp_path: Path) -> None:
    source_path = tmp_path / "main.py"
    source_path.write_text("print('hello')", encoding="utf-8")
    tabs = EditorTabs()

    editor = tabs.open_file(source_path)

    assert isinstance(editor, EditorPanel)
    assert tabs.active_editor is editor


def test_media_preview_can_be_closed_from_editor_tabs(tmp_path: Path) -> None:
    image_path = tmp_path / "preview.png"
    image_path.write_bytes(_ONE_PIXEL_PNG)
    tabs = EditorTabs()
    preview = tabs.open_image(image_path)

    tabs.close_preview(preview)

    assert tabs.page_num(preview) == -1
    assert tabs.get_n_pages() == 0
