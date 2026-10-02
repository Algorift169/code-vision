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
        split_terminal_factory: Callable[[Path], TerminalSession] | None = None,
    ) -> None:
        super().__init__()
        self.set_name("editor-tabs")
        self.set_scrollable(True)
        self.set_show_border(False)
        self.set_show_tabs(False)
        self._on_active_changed = on_active_changed
        self._on_terminal_closed = on_terminal_closed
        self._on_close_requested = on_close_requested
        self._split_terminal_factory = split_terminal_factory
        self._tab_labels: dict[int, Gtk.Label] = {}
        self._terminal_sessions: dict[int, TerminalSession] = {}
        self._terminal_panes: dict[int, Gtk.Box] = {}
        self._terminal_page_groups: dict[int, tuple[TerminalSession, ...]] = {}
        self._terminal_page_widgets: dict[int, Gtk.Widget] = {}
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
        if page is None:
            return None
        group = self._terminal_page_groups.get(id(page))
        if group is not None:
            for session in group:
                if session.terminal.has_focus():
                    return session
            return group[0]
        return self._terminal_sessions.get(id(page))

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

        page_number = self.append_page(terminal, self._terminal_tab_header(session))
        self._terminal_sessions[id(terminal)] = session
        self._set_terminal_page_group(terminal, (session,))
        self.set_tab_reorderable(terminal, True)
        self.set_show_tabs(True)
        self.set_current_page(page_number)
        terminal.grab_focus()
        self._notify_active_changed()
        return terminal

    def split_terminal(self, session: TerminalSession) -> Gtk.Widget:
        """Add a terminal pane beside the requested terminal, without a split limit."""
        page_number = -1
        root: Gtk.Widget | None = None
        sessions: tuple[TerminalSession, ...] = ()
        for index in range(self.get_n_pages()):
            page = self.get_nth_page(index)
            group = self._terminal_page_groups.get(id(page), ())
            if page is session.terminal or session in group:
                page_number = index
                root = page
                sessions = group or (session,)
                break

        if root is None:
            if session.terminal.get_parent() is None:
                return self.open_terminal(session)
            return session.terminal

        if self._split_terminal_factory is None:
            second_terminal = session.terminal.__class__()
            second_session = TerminalSession(
                terminal=second_terminal, directory=session.directory
            )
            if hasattr(second_session.terminal, "set_hexpand"):
                second_session.terminal.set_hexpand(True)
            if hasattr(second_session.terminal, "set_vexpand"):
                second_session.terminal.set_vexpand(True)
            second_session.terminal.set_name("terminal-view")
            second_session.terminal.add_css_class("terminal-view")
        else:
            second_session = self._split_terminal_factory(session.directory)
            second_session.terminal.set_name("terminal-view")
            second_session.terminal.add_css_class("terminal-view")

        new_pane = self._split_terminal_pane(second_session)
        if root is session.terminal:
            root_split = self._new_terminal_split()
            self.remove_page(page_number)
            first_pane = self._split_terminal_pane(session)
            root_split.set_start_child(first_pane)
            root_split.set_end_child(new_pane)
            title = session.directory.name or str(session.directory)
            page_number = self.append_page(root_split, self._split_tab_header(title, session))
            root = root_split
            self._remove_terminal_page_group(session.terminal)
            self.set_tab_reorderable(root_split, True)
        else:
            first_pane = self._terminal_panes.get(id(session.terminal))
            parent = first_pane.get_parent() if first_pane is not None else None
            if first_pane is None or not isinstance(parent, Gtk.Paned):
                return session.terminal

            nested_split = self._new_terminal_split()
            if parent.get_start_child() is first_pane:
                parent.set_start_child(None)
                nested_split.set_start_child(first_pane)
                nested_split.set_end_child(new_pane)
                parent.set_start_child(nested_split)
            elif parent.get_end_child() is first_pane:
                parent.set_end_child(None)
                nested_split.set_start_child(first_pane)
                nested_split.set_end_child(new_pane)
                parent.set_end_child(nested_split)
            else:
                return session.terminal

        self._terminal_sessions[id(session.terminal)] = session
        self._terminal_sessions[id(second_session.terminal)] = second_session
        self._terminal_panes[id(session.terminal)] = first_pane
        self._terminal_panes[id(second_session.terminal)] = new_pane
        group = sessions + (second_session,)
        self._set_terminal_page_group(root, group)
        self.set_show_tabs(True)
        self.set_current_page(page_number)
        second_session.terminal.grab_focus()
        self._notify_active_changed()
        return root

    @staticmethod
    def _new_terminal_split() -> Gtk.Paned:
        split = Gtk.Paned.new(Gtk.Orientation.VERTICAL)
        split.set_wide_handle(True)
        split.set_vexpand(True)
        split.set_hexpand(True)
        split.set_position(220)
        split.set_name("terminal-split")
        return split

    def _set_terminal_page_group(
        self, page: Gtk.Widget, group: tuple[TerminalSession, ...]
    ) -> None:
        page_id = id(page)
        self._terminal_page_groups[page_id] = group
        self._terminal_page_widgets[page_id] = page

    def _remove_terminal_page_group(self, page: Gtk.Widget) -> None:
        page_id = id(page)
        self._terminal_page_groups.pop(page_id, None)
        self._terminal_page_widgets.pop(page_id, None)

    def _split_tab_header(self, title: str, session: TerminalSession) -> Gtk.Box:
        tab_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        tab_label = Gtk.Label(label=f"Split Terminal: {title}")
        tab_label.add_css_class("editor-tab-label")
        tab_header.append(tab_label)

        close_button = Gtk.Button()
        close_button.set_child(Gtk.Image.new_from_icon_name("window-close-symbolic"))
        close_button.set_tooltip_text(f"Close split terminal in {session.directory}")
        close_button.add_css_class("editor-tab-close")
        close_button.connect("clicked", lambda *_args: self.close_terminal(session))
        tab_header.append(close_button)
        return tab_header

    def _terminal_tab_header(self, session: TerminalSession) -> Gtk.Box:
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
        return tab_header

    def _split_terminal_pane(self, session: TerminalSession) -> Gtk.Box:
        title = session.directory.name or str(session.directory)
        pane = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        pane.add_css_class("terminal-pane")
        pane.set_hexpand(True)
        pane.set_vexpand(True)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        header.add_css_class("terminal-pane-header")
        header.set_margin_start(8)
        header.set_margin_end(4)
        header.set_margin_top(2)
        header.set_margin_bottom(2)
        label = Gtk.Label(label=title)
        label.set_hexpand(True)
        label.set_xalign(0)
        label.add_css_class("terminal-pane-title")
        header.append(label)

        close_button = Gtk.Button()
        close_button.set_child(Gtk.Image.new_from_icon_name("window-close-symbolic"))
        close_button.set_tooltip_text(f"Close terminal pane in {session.directory}")
        close_button.add_css_class("editor-tab-close")
        close_button.connect(
            "clicked", lambda *_args: self._close_split_terminal(session)
        )
        header.append(close_button)

        pane.append(header)
        pane.append(session.terminal)
        return pane

    def _close_split_terminal(self, session: TerminalSession) -> None:
        page_number = -1
        root: Gtk.Widget | None = None
        group: tuple[TerminalSession, ...] = ()
        for index in range(self.get_n_pages()):
            page = self.get_nth_page(index)
            candidate_group = self._terminal_page_groups.get(id(page), ())
            if session in candidate_group:
                page_number = index
                root = page
                group = candidate_group
                break

        if page_number < 0 or len(group) < 2 or not isinstance(root, Gtk.Paned):
            return

        survivor = next(item for item in group if item is not session)
        pane = self._terminal_panes.get(id(session.terminal))
        parent = pane.get_parent() if pane is not None else None
        if pane is None or not isinstance(parent, Gtk.Paned):
            return

        if parent is root:
            if parent.get_start_child() is pane:
                parent.set_start_child(None)
            elif parent.get_end_child() is pane:
                parent.set_end_child(None)
            else:
                return
        else:
            grandparent = parent.get_parent()
            if not isinstance(grandparent, Gtk.Paned):
                return
            if parent.get_start_child() is pane:
                sibling = parent.get_end_child()
                parent.set_start_child(None)
                parent.set_end_child(None)
            elif parent.get_end_child() is pane:
                sibling = parent.get_start_child()
                parent.set_end_child(None)
                parent.set_start_child(None)
            else:
                return
            if sibling is None:
                return
            if grandparent.get_start_child() is parent:
                grandparent.set_start_child(None)
                grandparent.set_start_child(sibling)
            elif grandparent.get_end_child() is parent:
                grandparent.set_end_child(None)
                grandparent.set_end_child(sibling)
            else:
                return

        pane.remove(session.terminal)
        self._terminal_panes.pop(id(session.terminal), None)
        self._terminal_sessions.pop(id(session.terminal), None)
        remaining = tuple(item for item in group if item is not session)
        self._set_terminal_page_group(root, remaining)
        if self._on_terminal_closed is not None:
            self._on_terminal_closed(session)

        if len(remaining) == 1:
            survivor_pane = self._terminal_panes.pop(id(survivor.terminal), None)
            if survivor_pane is None:
                return
            self.remove_page(page_number)
            survivor_pane.remove(survivor.terminal)
            self._remove_terminal_page_group(root)
            survivor_page = self.append_page(
                survivor.terminal, self._terminal_tab_header(survivor)
            )
            self._set_terminal_page_group(survivor.terminal, (survivor,))
            self.set_tab_reorderable(survivor.terminal, True)
            self.set_current_page(survivor_page)

        self.set_show_tabs(True)
        if len(remaining) == 1:
            survivor.terminal.grab_focus()
        else:
            self.set_current_page(page_number)
        self._notify_active_changed()

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
        for page_number in range(self.get_n_pages()):
            page = self.get_nth_page(page_number)
            group = self._terminal_page_groups.get(id(page))
            if group is None and page is session.terminal:
                group = (session,)
            if group is None or session not in group:
                continue

            self.remove_page(page_number)
            for terminal_session in group:
                self._terminal_sessions.pop(id(terminal_session.terminal), None)
                self._terminal_panes.pop(id(terminal_session.terminal), None)
                if self._on_terminal_closed is not None:
                    self._on_terminal_closed(terminal_session)
            self._remove_terminal_page_group(page)
            if self.get_n_pages() == 0:
                self.set_show_tabs(False)
            self._notify_active_changed()
            return

        terminal = session.terminal
        for page_number in range(self.get_n_pages()):
            if self.get_nth_page(page_number) is terminal:
                self.remove_page(page_number)
                self._terminal_sessions.pop(id(terminal), None)
                self._terminal_panes.pop(id(terminal), None)
                self._remove_terminal_page_group(terminal)
                if self._on_terminal_closed is not None:
                    self._on_terminal_closed(session)
                if self.get_n_pages() == 0:
                    self.set_show_tabs(False)
                self._notify_active_changed()
                return

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
