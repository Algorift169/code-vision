"""GtkSourceView-based editor panel and text-editing operations.

This module builds the editor's source buffer and view, provides common
clipboard and comment-editing actions, expands abbreviations, and handles
loading and saving documents through the editor's services.
"""

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
    """Center editor panel providing source editing and file operations.

    The panel owns a GtkSourceView buffer, applies language-aware editing
    actions, and tracks the path and title of the document being edited.
    """

    def __init__(self, language_id: str | None = "cpp") -> None:
        """Create the editor view and optionally enable a source language.

        The constructor builds the editor header and scrollable source view,
        then creates a GtkSource buffer and associates it with the requested
        language when that language is available.

        Args:
            language_id: GtkSource language identifier used for highlighting,
                or ``None`` to leave the buffer language unspecified. The
                default language is C++.
        """
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

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_child(source_view)
        self.append(scrolled)

    def _language_id(self) -> str:
        """Return the active source language's normalized identifier.

        The identifier is used when selecting editing conventions such as
        comment syntax. If the buffer has no language, this method returns an
        empty string so callers can safely use ordinary string checks.
        """
        language = self.buffer.get_language()
        if language is None:
            return ""
        language_id = language.get_id()
        return language_id.lower() if isinstance(language_id, str) else ""

    def _comment_prefix_for_language(self) -> tuple[str, str]:
        """Choose the line-comment prefix and block-comment suffix.

        C-family languages use ``//`` for line comments. Other or unspecified
        languages use ``#``; the returned suffix is empty because line
        comments do not require a closing delimiter.
        """
        language_id = self._language_id()
        if "c" in language_id or "cpp" in language_id or "cxx" in language_id:
            return "//", ""
        return "#", ""

    @staticmethod
    def _line_prefix(text: str) -> tuple[str, str]:
        """Separate a line's indentation from its non-whitespace content.

        The indentation is returned unchanged so line-comment edits can insert
        or remove a comment marker without moving the code horizontally.
        """
        match = re.match(r"^\s*", text)
        indent = match.group(0) if match is not None else ""
        return indent, text[len(indent) :]

    @staticmethod
    def _as_text_iter(result: object) -> Gtk.TextIter:
        """Extract a text iterator from supported GTK return-value shapes.

        GTK bindings may expose an iterator directly or wrap it in an object
        or tuple. This helper normalizes those forms for editor operations
        that need a single insertion or start position.

        Raises:
            TypeError: If ``result`` has no supported Gtk.TextIter value.
        """
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
        """Extract the start and end iterators from a GTK bounds result.

        Buffer-bound APIs may return an object with ``start`` and ``end``
        attributes or a two-item tuple. Returning a consistent pair keeps
        save operations independent of that binding detail.

        Raises:
            TypeError: If ``bounds`` does not contain supported endpoints.
        """
        if hasattr(bounds, "start") and hasattr(bounds, "end"):
            return bounds.start, bounds.end
        if isinstance(bounds, tuple) and len(bounds) == 2:
            return bounds[0], bounds[1]
        raise TypeError(f"Expected start/end bounds, got {type(bounds).__name__}")

    def _toggle_line_comment(self, text: str, prefix: str) -> str:
        """Toggle a line-comment marker on every line in the given text.

        Each line is handled independently: an existing marker immediately
        after indentation is removed, otherwise the marker is inserted at
        that position. An empty input is treated as one empty line.
        """
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
        """Toggle block-comment delimiters around a text selection.

        If the selection already starts and ends with the supplied delimiters,
        those outer delimiters are removed. Otherwise the selection is wrapped
        with the prefix and suffix.
        """
        if text.startswith(prefix) and text.endswith(suffix):
            inner = text[len(prefix) : -len(suffix)]
            return inner
        return f"{prefix}{text}{suffix}"

    def undo(self) -> None:
        """Undo the most recent buffer change when history allows it.

        Some GtkSource buffer implementations may not expose undo support, so
        the action first checks for the capability and an available undo step.
        """
        if hasattr(self.buffer, "can_undo") and self.buffer.can_undo():
            self.buffer.undo()

    def redo(self) -> None:
        """Redo the next buffer change when history allows it.

        The buffer is changed only when it provides redo support and reports
        that a redo operation is currently available.
        """
        if hasattr(self.buffer, "can_redo") and self.buffer.can_redo():
            self.buffer.redo()

    def cut(self) -> None:
        """Cut selected text to the system clipboard.

        The operation is ignored for a read-only view, without a display, or
        when the buffer has no selection. Successful cuts leave the buffer
        editable and place the removed text on the display clipboard.
        """
        if not self.source_view.get_editable():
            return
        display = Gdk.Display.get_default()
        if display is not None and self.buffer.get_has_selection():
            self.buffer.cut_clipboard(display.get_clipboard(), True)

    def copy(self) -> None:
        """Copy selected text to the system clipboard.

        There is nothing to copy when the buffer has no selection. Clipboard
        access is also skipped when GTK has no default display, as can happen
        in headless operation.
        """
        if not self.buffer.get_has_selection():
            return
        display = Gdk.Display.get_default()
        if display is not None:
            self.buffer.copy_clipboard(display.get_clipboard())

    def paste(self) -> None:
        """Paste clipboard content at the current insertion point.

        Pasting is skipped when the view is read-only or no default display is
        available. Otherwise GtkSource requests clipboard content and inserts
        it into the current buffer.
        """
        if not self.source_view.get_editable():
            return
        display = Gdk.Display.get_default()
        if display is None:
            return
        self.buffer.paste_clipboard(display.get_clipboard(), None, True)

    def toggle_line_comment(self) -> None:
        """Toggle line comments for the selection or current cursor line.

        When text is selected, every selected line is updated using the
        language's line-comment prefix. Without a selection, only the line
        containing the insertion cursor is changed. Read-only views are left
        untouched.
        """
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
        """Toggle block comments around the selected buffer text.

        The action requires an editable view and an active selection. It uses
        the language's configured delimiters, substituting C-style block
        delimiters for languages whose line-comment marker has no block form.
        """
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
        """Expand an Emmet abbreviation immediately before the cursor.

        The candidate abbreviation is read from the current line up to the
        insertion point and passed to the Emmet expansion service. The buffer
        is modified only when the view is editable and the service recognizes
        the candidate.

        Returns:
            ``True`` when the abbreviation is replaced with expanded text;
            otherwise ``False`` when editing is unavailable or there is no
            recognized abbreviation.
        """
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
        """Change the buffer language used for syntax highlighting.

        A ``None`` identifier clears the language. An identifier that the
        GtkSource language manager cannot resolve is passed through as no
        language, leaving the buffer without language-specific highlighting.
        """
        language = (
            self.language_manager.get_language(language_id)
            if language_id is not None
            else None
        )
        self.buffer.set_language(language)

    def open_file(self, path: Path) -> None:
        """Load a file and update the editor's path, language, and title.

        The supplied path is expanded and resolved before the contents are
        read as UTF-8. Invalid byte sequences are replaced rather than
        preventing the file from opening. The language is inferred from the
        resolved path and the buffer is marked unmodified after loading.
        """
        self.file_path = path.expanduser().resolve()
        self.buffer.set_text(
            self.file_path.read_text(encoding="utf-8", errors="replace")
        )
        language = self.language_manager.guess_language(str(self.file_path), None)
        self.buffer.set_language(language)
        self.buffer.set_modified(False)
        self.title.set_text(self.file_path.name)

    def save_file(self, save_service: SaveService, path: Path | None = None) -> Path:
        """Save the buffer to the given path or its current file path.

        The buffer's complete text is passed to the save service. On success,
        the returned destination becomes the editor's current file, its
        language is inferred again from that path, and the modified indicator
        is cleared.

        Args:
            save_service: Service responsible for persisting the buffer text.
            path: Optional destination path; defaults to the current file path.

        Returns:
            The resolved path written by the save service.

        Raises:
            ValueError: If neither ``path`` nor a current file path is set.
        """
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
