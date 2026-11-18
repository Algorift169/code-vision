from __future__ import annotations

import math
from pathlib import Path

import gi

gi.require_version("Gio", "2.0")
gi.require_version("Gtk", "4.0")
gi.require_version("Pango", "1.0")
from gi.repository import Gio, Gtk, Pango

from .zoom import SpaceZoom


class ImportItem(Gtk.Frame):
    """A draggable file card placed on the Space board."""

    WIDTH = 184
    HEIGHT = 132

    def __init__(
        self,
        path: Path,
        content_type: str,
        mime_type: str,
        zoom: SpaceZoom,
        position: tuple[float, float],
    ) -> None:
        super().__init__()
        self.path = path
        self.content_type = content_type
        self.mime_type = mime_type
        self.zoom = zoom
        self.x, self.y = position
        self.display_name = path.name
        self.set_name("space-import-item")
        self.add_css_class("space-import-item")
        self.set_tooltip_text(str(path))

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        content.set_margin_top(8)
        content.set_margin_bottom(8)
        content.set_margin_start(8)
        content.set_margin_end(8)
        if mime_type.startswith("image/"):
            preview = Gtk.Picture.new_for_filename(str(path))
            preview.set_can_shrink(True)
            preview.set_content_fit(Gtk.ContentFit.CONTAIN)
            self.preview = preview
        else:
            icon = Gio.content_type_get_symbolic_icon(content_type)
            preview = Gtk.Image.new_from_gicon(icon)
            self.preview = preview
        content.append(preview)

        self.filename_label = Gtk.Label(label=self.display_name)
        self.filename_label.set_xalign(0.5)
        self.filename_label.set_wrap(True)
        self.filename_label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self.filename_label.set_lines(2)
        content.append(self.filename_label)
        self.set_child(content)
        self.apply_zoom()

    def set_display_name(self, name: str) -> None:
        display_name = name.strip()
        if not display_name:
            raise ValueError("Imported file names cannot be empty.")
        self.display_name = display_name
        self.filename_label.set_text(display_name)

    def apply_zoom(self) -> None:
        scale = self.zoom.scale
        self.set_size_request(
            math.ceil(self.WIDTH * scale),
            math.ceil(self.HEIGHT * scale),
        )
        self.preview.set_size_request(
            math.ceil(160 * scale),
            math.ceil(84 * scale),
        )
        if isinstance(self.preview, Gtk.Image):
            self.preview.set_pixel_size(math.ceil(48 * scale))
        attributes = Pango.AttrList()
        attributes.insert(Pango.attr_size_new(round(10 * scale * Pango.SCALE)))
        self.filename_label.set_attributes(attributes)
