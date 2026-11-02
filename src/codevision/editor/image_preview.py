from __future__ import annotations

from pathlib import Path

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gio, Gtk


class ImagePreview(Gtk.Box):
    """Read-only editor page for previewing a project image."""

    def __init__(self, path: Path) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_name("image-preview")
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

        self.picture = Gtk.Picture()
        self.picture.set_name("image-preview-picture")
        self.picture.set_content_fit(Gtk.ContentFit.CONTAIN)
        self.picture.set_can_shrink(True)
        self.picture.set_hexpand(True)
        self.picture.set_vexpand(True)
        texture = Gdk.Texture.new_from_file(
            Gio.File.new_for_path(str(self.file_path))
        )
        self.picture.set_paintable(texture)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_hexpand(True)
        scrolled.set_vexpand(True)
        scrolled.set_child(self.picture)
        self.append(scrolled)


__all__ = ["ImagePreview"]
