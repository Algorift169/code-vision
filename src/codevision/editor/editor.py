from __future__ import annotations

from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("GtkSource", "5")
from gi.repository import Gtk, GtkSource

from ..services.save import SaveService


class EditorPanel(Gtk.Box):
    """Center editor panel using GtkSourceView."""

    def __init__(self, language_id: str | None = "cpp") -> None:
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
        self.title = title

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
        self.source_view = source_view

        manager = GtkSource.LanguageManager()
        language = manager.get_language(language_id) if language_id is not None else None
        buffer = GtkSource.Buffer()
        if language is not None:
            buffer.set_language(language)
        source_view.set_buffer(buffer)
        self.buffer = buffer
        self.language_manager = manager
        self.file_path: Path | None = None

        """The EditorPanel class provides a text editor panel using GtkSourceView, allowing"""
        """users to edit code with syntax highlighting and other features. It supports setting"""
        """the programming language for syntax highlighting, opening files, and saving files."""
        """The panel includes a header with a title and a scrollable text area for editing code."""
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_child(source_view)
        self.append(scrolled)

    def set_language(self, language_id: str | None) -> None:
        language = (
            self.language_manager.get_language(language_id)
            if language_id is not None
            else None
        )
        self.buffer.set_language(language)

    def open_file(self, path: Path) -> None:
        """Display a selected project file in the editor."""
        self.file_path = path.expanduser().resolve()
        self.buffer.set_text(
            self.file_path.read_text(encoding="utf-8", errors="replace")
        )
        language = self.language_manager.guess_language(str(self.file_path), None)
        self.buffer.set_language(language)
        self.buffer.set_modified(False)
        self.title.set_text(self.file_path.name)

    def save_file(self, save_service: SaveService, path: Path | None = None) -> Path:
        """Save the current buffer to its existing or newly selected path."""
        target = path or self.file_path
        if target is None:
            raise ValueError("A file path is required to save this buffer")

        start, end = self.buffer.get_bounds()
        content = self.buffer.get_text(start, end, True)
        saved_path = save_service.save_file(target, content).resolve()
        self.file_path = saved_path
        language = self.language_manager.guess_language(str(saved_path), None)
        self.buffer.set_language(language)
        self.buffer.set_modified(False)
        self.title.set_text(saved_path.name)
        return saved_path
