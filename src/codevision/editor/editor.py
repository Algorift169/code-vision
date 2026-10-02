from __future__ import annotations

import re
from pathlib import Path

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
gi.require_version("GtkSource", "5")
from gi.repository import Gdk, Gtk, GtkSource

from ..services.emmet import EmmetExpansionService
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

    def _language_id(self) -> str:
        language = self.buffer.get_language()
        if language is None:
            return ""
        language_id = language.get_id()
        return language_id.lower() if isinstance(language_id, str) else ""

    def _comment_prefix_for_language(self) -> tuple[str, str]:
        language_id = self._language_id()
        if "c" in language_id or "cpp" in language_id or "cxx" in language_id:
            return "//", ""
        return "#", ""

    @staticmethod
    def _line_prefix(text: str) -> tuple[str, str]:
        match = re.match(r"^\s*", text)
        indent = match.group(0) if match is not None else ""
        return indent, text[len(indent) :]

    @staticmethod
    def _as_text_iter(result: object) -> Gtk.TextIter:
        if isinstance(result, Gtk.TextIter):
            return result
        if hasattr(result, "iter"):
            return result.iter
        if hasattr(result, "start") and hasattr(result, "end"):
            return result.start
        if isinstance(result, tuple) and len(result) == 2:
            return result[1] if isinstance(result[1], Gtk.TextIter) else result[0]
        raise TypeError(f"Expected Gtk.TextIter-compatible result, got {type(result).__name__}")

    @staticmethod
    def _bounds_as_iters(bounds: object) -> tuple[Gtk.TextIter, Gtk.TextIter]:
        if hasattr(bounds, "start") and hasattr(bounds, "end"):
            return bounds.start, bounds.end
        if isinstance(bounds, tuple) and len(bounds) == 2:
            return bounds[0], bounds[1]
        raise TypeError(f"Expected start/end bounds, got {type(bounds).__name__}")

    def _toggle_line_comment(self, text: str, prefix: str) -> str:
        lines = text.splitlines() or [""]
        updated: list[str] = []
        for line in lines:
            indent, body = self._line_prefix(line)
            if body.startswith(prefix):
                body = body[len(prefix) :]
            else:
                body = f"{prefix}{body}"
            updated.append(f"{indent}{body}")
        return "\n".join(updated)

    def _toggle_block_comment(self, text: str, prefix: str, suffix: str) -> str:
        if text.startswith(prefix) and text.endswith(suffix):
            inner = text[len(prefix) : -len(suffix)]
            return inner
        return f"{prefix}{text}{suffix}"

    def undo(self) -> None:
        if hasattr(self.buffer, "can_undo") and self.buffer.can_undo():
            self.buffer.undo()

    def redo(self) -> None:
        if hasattr(self.buffer, "can_redo") and self.buffer.can_redo():
            self.buffer.redo()

    def cut(self) -> None:
        if not self.source_view.get_editable():
            return
        display = Gdk.Display.get_default()
        if display is not None and self.buffer.get_has_selection():
            self.buffer.cut_clipboard(display.get_clipboard(), True)

    def copy(self) -> None:
        if not self.buffer.get_has_selection():
            return
        display = Gdk.Display.get_default()
        if display is not None:
            self.buffer.copy_clipboard(display.get_clipboard())

    def paste(self) -> None:
        if not self.source_view.get_editable():
            return
        display = Gdk.Display.get_default()
        if display is None:
            return
        self.buffer.paste_clipboard(display.get_clipboard(), None, True)

    def toggle_line_comment(self) -> None:
        if not self.source_view.get_editable():
            return
        buffer = self.buffer
        if buffer.get_has_selection():
            start, end = buffer.get_selection_bounds()
            source = buffer.get_text(start, end, True)
            prefix, _suffix = self._comment_prefix_for_language()
            replacement = self._toggle_line_comment(source, prefix)
            buffer.delete(start, end)
            buffer.insert_at_cursor(replacement)
            return

        insert_mark = buffer.get_insert()
        cursor = buffer.get_iter_at_mark(insert_mark)
        line_start = self._as_text_iter(buffer.get_iter_at_line(cursor.get_line()))
        line_end = self._as_text_iter(buffer.get_iter_at_line(cursor.get_line() + 1))
        source = buffer.get_text(line_start, line_end, True)
        prefix, _suffix = self._comment_prefix_for_language()
        replacement = self._toggle_line_comment(source.rstrip("\n"), prefix)
        buffer.delete(line_start, line_end)
        buffer.insert(line_start, replacement + "\n")

    def toggle_block_comment(self) -> None:
        if not self.source_view.get_editable():
            return
        buffer = self.buffer
        if not buffer.get_has_selection():
            return
        start, end = buffer.get_selection_bounds()
        text = buffer.get_text(start, end, True)
        prefix, suffix = self._comment_prefix_for_language()
        if prefix == "#":
            prefix, suffix = "/*", "*/"
        replacement = self._toggle_block_comment(text, prefix, suffix)
        buffer.delete(start, end)
        buffer.insert_at_cursor(replacement)

    def expand_abbreviation(self) -> bool:
        if not self.source_view.get_editable():
            return False
        buffer = self.buffer
        insert_mark = buffer.get_insert()
        cursor = buffer.get_iter_at_mark(insert_mark)
        line_start = self._as_text_iter(buffer.get_iter_at_line(cursor.get_line()))
        line_end = cursor
        text = buffer.get_text(line_start, line_end, True)
        match = re.search(r"([A-Za-z0-9_#.[\]>*+-]+)$", text)
        if match is None:
            return False
        abbreviation = match.group(1)
        expanded = EmmetExpansionService().expand(abbreviation)
        if expanded is None:
            return False
        buffer.delete(line_start, line_end)
        buffer.insert(line_start, expanded)
        return True

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

        start, end = self._bounds_as_iters(self.buffer.get_bounds())
        content = self.buffer.get_text(start, end, True)
        saved_path = save_service.save_file(target, content).resolve()
        self.file_path = saved_path
        language = self.language_manager.guess_language(str(saved_path), None)
        self.buffer.set_language(language)
        self.buffer.set_modified(False)
        self.title.set_text(saved_path.name)
        return saved_path
