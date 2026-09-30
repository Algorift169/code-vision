from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from ..services.save import SaveService
from ..services.terminal import TerminalSession
from .editor import EditorPanel


class EditorTabs(Gtk.Notebook):
    """Notebook containing editor files and embedded terminal sessions."""

    def __init__(
        self,
        on_active_changed: Callable[[Gtk.Widget | None], None] | None = None,
        on_terminal_closed: Callable[[TerminalSession], None] | None = None,
        on_close_requested: Callable[[EditorPanel], None] | None = None,
    ) -> None:
        super().__init__()
        self.set_name("editor-tabs")
        self.set_scrollable(True)
        self.set_show_border(False)
        self.set_show_tabs(False)
        self._on_active_changed = on_active_changed
        self._on_terminal_closed = on_terminal_closed
        self._on_close_requested = on_close_requested
        self._tab_labels: dict[int, Gtk.Label] = {}
        self._terminal_sessions: dict[int, TerminalSession] = {}
        self.connect("switch-page", self._on_switch_page)

    @property
    def active_page(self) -> Gtk.Widget | None:
        page = self.get_nth_page(self.get_current_page())
        return page if isinstance(page, Gtk.Widget) else None

    @property
    def active_editor(self) -> EditorPanel | None:
        page = self.active_page
        return page if isinstance(page, EditorPanel) else None

    @property
    def active_terminal(self) -> TerminalSession | None:
        page = self.active_page
        return self._terminal_sessions.get(id(page)) if page is not None else None

    @property
    def editors(self) -> tuple[EditorPanel, ...]:
        return tuple(
            page
            for page_number in range(self.get_n_pages())
            if isinstance((page := self.get_nth_page(page_number)), EditorPanel)
        )

    def open_file(self, path: Path) -> EditorPanel:
        """Open a file in its own editor tab, selecting it if already open."""
        resolved_path = path.expanduser().resolve()
        for page_number in range(self.get_n_pages()):
            page = self.get_nth_page(page_number)
            if isinstance(page, EditorPanel) and page.file_path == resolved_path:
                self.set_current_page(page_number)
                return page

        editor = EditorPanel()
        editor.set_name("editor-panel")
        editor.open_file(resolved_path)
        return self._add_editor(editor, resolved_path.name)

    def new_document(
        self, title: str, language_id: str | None = None
    ) -> EditorPanel:
        editor = EditorPanel(language_id=language_id)
        editor.set_name("editor-panel")
        editor.title.set_text(title)
        return self._add_editor(editor, title)

    def _add_editor(self, editor: EditorPanel, title: str) -> EditorPanel:
        tab_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        tab_label = Gtk.Label(label=title)
        tab_label.add_css_class("editor-tab-label")
        tab_header.append(tab_label)

        close_button = Gtk.Button()
        close_button.set_child(Gtk.Image.new_from_icon_name("window-close-symbolic"))
        close_button.set_tooltip_text(f"Close {title}")
        close_button.add_css_class("editor-tab-close")
        close_button.connect("clicked", lambda *_args: self.request_close_editor(editor))
        tab_header.append(close_button)

        page_number = self.append_page(editor, tab_header)
        self._tab_labels[id(editor)] = tab_label
        editor.buffer.connect(
            "notify::modified", lambda *_args: self._update_tab_label(editor)
        )
        self.set_tab_reorderable(editor, True)
        self.set_show_tabs(True)
        self.set_current_page(page_number)
        editor.source_view.grab_focus()
        self._notify_active_changed()
        return editor

    def open_terminal(self, session: TerminalSession) -> Gtk.Widget:
        """Show an embedded terminal session in its own notebook tab."""
        terminal = session.terminal
        terminal.set_name("terminal-view")
        terminal.add_css_class("terminal-view")
        terminal.set_hexpand(True)
        terminal.set_vexpand(True)

        title = session.directory.name or str(session.directory)
        tab_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        tab_label = Gtk.Label(label=f"Terminal: {title}")
        tab_label.add_css_class("editor-tab-label")
        tab_header.append(tab_label)

        close_button = Gtk.Button()
        close_button.set_child(Gtk.Image.new_from_icon_name("window-close-symbolic"))
        close_button.set_tooltip_text(f"Close terminal in {session.directory}")
        close_button.add_css_class("editor-tab-close")
        close_button.connect("clicked", lambda *_args: self.close_terminal(session))
        tab_header.append(close_button)

        page_number = self.append_page(terminal, tab_header)
        self._terminal_sessions[id(terminal)] = session
        self.set_tab_reorderable(terminal, True)
        self.set_show_tabs(True)
        self.set_current_page(page_number)
        terminal.grab_focus()
        self._notify_active_changed()
        return terminal

    def save_active(
        self, save_service: SaveService, path: Path | None = None
    ) -> Path:
        editor = self.active_editor
        if editor is None:
            raise ValueError("There is no active editor tab")
        return self.save_editor(editor, save_service, path)

    def save_editor(
        self,
        editor: EditorPanel,
        save_service: SaveService,
        path: Path | None = None,
    ) -> Path:
        saved_path = editor.save_file(save_service, path)
        self._update_tab_label(editor)
        return saved_path

    def request_close_editor(self, editor: EditorPanel) -> None:
        if self._on_close_requested is None:
            self.close_editor(editor)
        else:
            self._on_close_requested(editor)

    def _update_tab_label(self, editor: EditorPanel) -> None:
        tab_label = self._tab_labels.get(id(editor))
        if tab_label is None:
            return
        title = editor.file_path.name if editor.file_path is not None else editor.title.get_text()
        tab_label.set_text(f"{title}{'*' if editor.buffer.get_modified() else ''}")

    def close_editor(self, editor: EditorPanel) -> None:
        page_number = self.page_num(editor)
        if page_number < 0:
            return

        self.remove_page(page_number)
        self._tab_labels.pop(id(editor), None)
        if self.get_n_pages() == 0:
            self.set_show_tabs(False)
        self._notify_active_changed()

    def close_terminal(self, session: TerminalSession) -> None:
        terminal = session.terminal
        page_number = self.page_num(terminal)
        if page_number < 0:
            return

        self.remove_page(page_number)
        self._terminal_sessions.pop(id(terminal), None)
        if self._on_terminal_closed is not None:
            self._on_terminal_closed(session)
        if self.get_n_pages() == 0:
            self.set_show_tabs(False)
        self._notify_active_changed()

    def close_all_terminals(self) -> None:
        for session in tuple(self._terminal_sessions.values()):
            self.close_terminal(session)

    def _on_switch_page(
        self, _notebook: Gtk.Notebook, _page: Gtk.Widget, _page_number: int
    ) -> None:
        self._notify_active_changed()

    def _notify_active_changed(self) -> None:
        if self._on_active_changed is not None:
            self._on_active_changed(self.active_page)
