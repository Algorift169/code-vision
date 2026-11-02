from __future__ import annotations

from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk


class VideoPreview(Gtk.Box):
    """Video player page for previewing a project video."""

    def __init__(self, path: Path) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_name("video-preview")
        self.add_css_class("panel")
        self.file_path = path.expanduser().resolve()

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header.set_margin_top(10)
        header.set_margin_bottom(8)
        header.set_margin_start(12)
        header.set_margin_end(12)
        header.add_css_class("panel-header")

        title = Gtk.Label(label=self.file_path.name)
        title.set_halign(Gtk.Align.START)
        title.set_hexpand(True)
        title.add_css_class("section-title")
        header.append(title)
        self.append(header)

        self.video = Gtk.Video.new_for_filename(str(self.file_path))
        self.video.set_autoplay(False)
        self.video.set_loop(False)
        self.video.set_hexpand(True)
        self.video.set_vexpand(True)

        player = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        player.set_halign(Gtk.Align.CENTER)
        player.set_valign(Gtk.Align.CENTER)
        player.set_hexpand(True)
        player.set_vexpand(True)
        player.append(self.video)

        stream = self.video.get_media_stream()
        if stream is not None:
            controls = Gtk.MediaControls.new(stream)
            controls.set_hexpand(True)
            player.append(controls)

            self.error_label = Gtk.Label()
            self.error_label.set_wrap(True)
            self.error_label.add_css_class("explorer-error")
            self.error_label.set_visible(False)
            player.append(self.error_label)
            stream.connect("notify::error", self._on_stream_error)
        else:
            self.error_label = None

        self.append(player)

    def _on_stream_error(self, stream: Gtk.MediaStream, _property: object) -> None:
        error = stream.get_error()
        if error is not None and self.error_label is not None:
            self.error_label.set_text(f"Could not play video: {error}")
            self.error_label.set_visible(True)


__all__ = ["VideoPreview"]
