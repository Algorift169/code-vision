from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("GtkSource", "5")
from gi.repository import Gtk, GtkSource


class EditorPanel(Gtk.Box):
    """Center editor panel using GtkSourceView."""

    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_name("editor-panel")
        self.add_css_class("panel")

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header.set_margin_top(10)
        header.set_margin_bottom(8)
        header.set_margin_start(12)
        header.set_margin_end(12)
        header.add_css_class("panel-header")

        title = Gtk.Label(label="Editor")
        title.set_halign(Gtk.Align.START)
        title.add_css_class("section-title")
        header.append(title)

        self.append(header)

        source_view = GtkSource.View()
        source_view.set_name("code-editor")
        source_view.set_show_line_numbers(True)
        source_view.set_auto_indent(True)
        source_view.set_tab_width(4)
        source_view.set_indent_width(4)
        source_view.set_insert_spaces_instead_of_tabs(True)
        source_view.set_vexpand(True)
        source_view.set_hexpand(True)
        source_view.set_margin_top(6)
        source_view.set_margin_bottom(6)
        source_view.set_margin_start(6)
        source_view.set_margin_end(6)

        manager = GtkSource.LanguageManager()
        language = manager.get_language("cpp")
        buffer = GtkSource.Buffer()
        if language is not None:
            buffer.set_language(language)
        source_view.set_buffer(buffer)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_child(source_view)
        self.append(scrolled)
