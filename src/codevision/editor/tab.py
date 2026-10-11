"""Notebook pages for source editors, browser tabs, and terminal sessions.

The tab manager coordinates selection, close requests, save operations, and
the terminal-session groups needed to manage nested terminal splits. It also
provides a small in-memory page implementation when no GTK display exists.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gtk

from ..services.save import SaveService
from ..services.terminal import TerminalSession
from ..ui.kong_browser import KongBrowser
from .editor import EditorPanel


class EditorTabs(Gtk.Notebook):
    """Manage editor, browser, and terminal pages in a notebook.

    The manager keeps tab labels and terminal-session metadata synchronized
    with notebook pages, routes editor close requests to an optional handler,
    and notifies listeners when the active page changes. In headless mode it
    stores pages locally instead of initializing the GTK notebook widget.
    """

    def __init__(
        self,
        on_active_changed: Callable[[Gtk.Widget | None], None] | None = None,
        on_terminal_closed: Callable[[TerminalSession], None] | None = None,
        on_close_requested: Callable[[EditorPanel], None] | None = None,
        split_terminal_factory: Callable[[Path], TerminalSession] | None = None,
    ) -> None:
        """Initialize the notebook and register optional lifecycle callbacks.

        With a display, this configures the GTK notebook and subscribes to its
        page-switch signal. Without a display, it initializes the local page
        model used by the overridden notebook methods.

        Args:
            on_active_changed: Receives the newly active page after a page
                selection or removal.
            on_terminal_closed: Receives each terminal session as it is
                removed, including sessions in a split page.
            on_close_requested: Optional owner callback for editor close
                requests; when omitted, requested editors close immediately.
            split_terminal_factory: Optional factory for creating another
                terminal session in the same working directory as a split.
        """
        self._headless = Gdk.Display.get_default() is None
        if self._headless:
            self._on_active_changed = on_active_changed
            self._on_terminal_closed = on_terminal_closed
            self._on_close_requested = on_close_requested
            self._split_terminal_factory = split_terminal_factory
            self._tab_labels: dict[int, Gtk.Label] = {}
            self._terminal_sessions: dict[int, TerminalSession] = {}
            self._terminal_panes: dict[int, Gtk.Box] = {}
            self._terminal_page_groups: dict[int, tuple[TerminalSession, ...]] = {}
            self._terminal_page_widgets: dict[int, Gtk.Widget] = {}
            self._pages: list[Gtk.Widget] = []
            self._page_headers: list[Gtk.Widget] = []
            self._current_page = -1
            self._show_tabs = False
            return

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

    def append_page(self, child: Gtk.Widget, tab_label: Gtk.Widget | None = None) -> int:
        """Append a page and return its resulting index.

        In headless mode, the page and optional header are recorded locally
        and the new page becomes current. With a GTK display, insertion is
        delegated to the parent notebook implementation.
        """
        if self._headless:
            self._pages.append(child)
            if tab_label is not None:
                self._page_headers.append(tab_label)
            self._current_page = len(self._pages) - 1
            return self._current_page
        return super().append_page(child, tab_label)

    def remove_page(self, page_number: int) -> None:
        """Remove a page by index, ignoring invalid headless indices.

        The headless implementation also removes its matching header when
        present and adjusts the current-page index to the remaining pages.
        """
        if self._headless:
            if 0 <= page_number < len(self._pages):
                self._pages.pop(page_number)
                if page_number < len(self._page_headers):
                    self._page_headers.pop(page_number)
                self._current_page = min(self._current_page, max(len(self._pages) - 1, -1))
            return
        super().remove_page(page_number)

    def get_n_pages(self) -> int:
        """Return the current number of notebook pages.

        Headless mode reports the local page-list length; otherwise the
        result comes from Gtk.Notebook.
        """
        if self._headless:
            return len(self._pages)
        return super().get_n_pages()

    def get_nth_page(self, page_number: int) -> Gtk.Widget | None:
        """Return the page at an index when it exists.

        The headless page model returns ``None`` for negative or out-of-range
        indexes, matching the optional return value expected by callers.
        """
        if self._headless:
            if 0 <= page_number < len(self._pages):
                return self._pages[page_number]
            return None
        return super().get_nth_page(page_number)

    def get_current_page(self) -> int:
        """Return the index of the currently selected page.

        If no page is selected, the notebook reports ``-1``. Headless mode
        reads the index maintained by its local page model.
        """
        if self._headless:
            return self._current_page
        return super().get_current_page()

    def set_current_page(self, page_number: int) -> None:
        """Select a page by index when it exists.

        The headless implementation updates its current index only for a valid
        page; the GTK implementation delegates selection to the notebook.
        """
        if self._headless:
            if 0 <= page_number < len(self._pages):
                self._current_page = page_number
            return
        super().set_current_page(page_number)

    def set_show_tabs(self, visible: bool) -> None:
        """Show or hide the notebook's tab strip.

        GTK updates the actual widget property. In headless mode, the
        requested visibility is stored for callers that need to inspect it.
        """
        if self._headless:
            self._show_tabs = visible
            return
        super().set_show_tabs(visible)

    def page_num(self, child: Gtk.Widget) -> int:
        """Find a child's page index by object identity.

        Returns ``-1`` when the widget is not present in the notebook. The
        headless implementation searches its local page collection.
        """
        if self._headless:
            for index, page in enumerate(self._pages):
                if page is child:
                    return index
            return -1
        return super().page_num(child)

    def set_tab_reorderable(self, _child: Gtk.Widget, _reorderable: bool) -> None:
        """Configure whether a notebook page can be dragged to a new position.

        This presentation-only setting has no effect in headless mode, where
        there is no GTK tab strip to reorder.
        """
        if self._headless:
            return
        super().set_tab_reorderable(_child, _reorderable)

    def set_scrollable(self, _scrollable: bool) -> None:
        """Configure whether the GTK tab strip can scroll when crowded.

        The setting is delegated only when a display-backed notebook exists;
        headless mode has no visual tab strip.
        """
        if self._headless:
            return
        super().set_scrollable(_scrollable)

    def set_show_border(self, _show_border: bool) -> None:
        """Configure notebook border visibility for the GTK presentation.

        Headless mode skips this presentation setting because its local page
        model does not render a notebook border.
        """
        if self._headless:
            return
        super().set_show_border(_show_border)

    @property
    def active_page(self) -> Gtk.Widget | None:
        """Return the selected page when the current index resolves to a widget.

        An empty notebook or a page lookup that does not produce a Gtk.Widget
        results in ``None``.
        """
        page = self.get_nth_page(self.get_current_page())
        return page if isinstance(page, Gtk.Widget) else None

    @property
    def active_editor(self) -> EditorPanel | None:
        """Return the selected page only when it is an editor panel.

        Browser pages, terminal pages, and an empty notebook all produce
        ``None``.
        """
        page = self.active_page
        return page if isinstance(page, EditorPanel) else None

    @property
    def active_terminal(self) -> TerminalSession | None:
        """Return the terminal session associated with the selected page.

        For a split-terminal page, the focused terminal session is preferred;
        if none has focus, the first session in the page's group is used. A
        non-split terminal page is resolved through the terminal-session map.
        Editor and browser pages return ``None``.
        """
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
        """Return editor pages in their current notebook order.

        Non-editor pages are omitted. The result is a tuple snapshot, so
        changing notebook pages later does not change this returned value.
        """
        return tuple(
            page
            for page_number in range(self.get_n_pages())
            if isinstance((page := self.get_nth_page(page_number)), EditorPanel)
        )

    def open_file(self, path: Path) -> EditorPanel:
        """Open a file in its own tab, selecting its tab if already open.

        The path is expanded and resolved before comparison. If an editor
        already has that resolved path, its page is selected and reused;
        otherwise a new editor is created, loaded, and added to the notebook.

        Args:
            path: File path to resolve and display in an editor.

        Returns:
            The existing or newly created editor panel for the file.
        """
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
        """Create a blank editor document and select its new page.

        The requested title is shown in the editor and tab header. The
        optional language identifier controls initial syntax highlighting.
        """
        editor = EditorPanel(language_id=language_id)
        editor.set_name("editor-panel")
        editor.title.set_text(title)
        return self._add_editor(editor, title)

    def open_kong_browser(
        self, initial_url: str | None = None, *, force_new: bool = False
    ) -> KongBrowser:
        """Open a browser page, optionally reusing the existing browser tab.

        Unless ``force_new`` is true, the first existing Kong browser page is
        selected and reused. A supplied address is loaded into that page. If
        no page is available or a new page is requested, a browser is created
        with a callback that opens further browser tabs.

        Args:
            initial_url: Optional address to load in the selected browser.
            force_new: Always create a separate browser tab when true.

        Returns:
            The reused or newly created browser widget.
        """
        if not force_new:
            for page_number in range(self.get_n_pages()):
                page = self.get_nth_page(page_number)
                if isinstance(page, KongBrowser):
                    self.set_current_page(page_number)
                    if initial_url:
                        page.load_url(initial_url)
                    return page

        browser = KongBrowser(
            initial_url=initial_url,
            on_new_tab=lambda: self.open_kong_browser(force_new=True),
        )
        if self._headless:
            self.append_page(browser, "🌐 Kong Browser")
            self.set_show_tabs(True)
            self.set_current_page(len(self._pages) - 1)
            return browser

        tab_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        tab_label = Gtk.Label(label="🌐 Kong Browser")
        tab_label.add_css_class("editor-tab-label")
        tab_header.append(tab_label)

        close_button = Gtk.Button()
        close_button.set_child(Gtk.Image.new_from_icon_name("window-close-symbolic"))
        close_button.set_tooltip_text("Close Kong Browser")
        close_button.add_css_class("editor-tab-close")
        close_button.connect("clicked", lambda *_args: self.close_kong_browser(browser))
        tab_header.append(close_button)

        page_number = self.append_page(browser, tab_header)
        self.set_tab_reorderable(browser, True)
        self.set_show_tabs(True)
        self.set_current_page(page_number)
        self._notify_active_changed()
        return browser

    def close_kong_browser(self, browser: KongBrowser) -> None:
        """Remove and destroy the specified browser tab when it is open.

        The active-page listener is notified after removal. The tab strip is
        hidden when closing this page leaves the notebook empty; a browser
        that is not part of the notebook is left unchanged.
        """
        for page_number in range(self.get_n_pages()):
            page = self.get_nth_page(page_number)
            if page is browser:
                self.remove_page(page_number)
                browser.destroy()
                if self.get_n_pages() == 0:
                    self.set_show_tabs(False)
                self._notify_active_changed()
                return

    def _add_editor(self, editor: EditorPanel, title: str) -> EditorPanel:
        """Add an editor page with a close button and modified-state tracking.

        The tab is made reorderable, selected, and focused after insertion.
        Buffer modification notifications update the displayed label, and
        the active-page listener is notified once the editor becomes active.
        """
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
        """Show a terminal session in its own notebook tab and focus it.

        The session is registered against the terminal widget and page group,
        given a closable tab header, and made the selected page.

        Args:
            session: Terminal session whose widget should become a notebook page.

        Returns:
            The terminal widget inserted into the notebook.
        """
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
        """Add a terminal pane beside the requested terminal.

        If the session belongs to a standard terminal page, that page is
        replaced by a vertical split. If it belongs to an existing split,
        another split is nested beside its pane. A second session is created
        through the optional factory, or by constructing the same terminal
        widget type when no factory is configured.

        If the requested session is not displayed, it is opened as a new page
        when its widget has no parent. If it cannot be placed into the current
        page structure, the existing terminal widget is returned unchanged.

        Args:
            session: The terminal session whose page or pane should be split.

        Returns:
            The root page widget for the resulting split, or the terminal
            widget when no split could be created.
        """
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
        """Create a vertically oriented container for terminal panes.

        The returned paned widget expands with its parent, uses a wide handle,
        and starts with a practical initial divider position.
        """
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
        """Associate a notebook page with its terminal sessions.

        Both the group and its page widget are retained by object identity so
        split-session metadata can be found and cleaned up consistently.
        """
        page_id = id(page)
        self._terminal_page_groups[page_id] = group
        self._terminal_page_widgets[page_id] = page

    def _remove_terminal_page_group(self, page: Gtk.Widget) -> None:
        """Discard the saved terminal-group and widget entries for a page.

        This removes metadata only; callers remain responsible for removing
        the page itself and closing its sessions.
        """
        page_id = id(page)
        self._terminal_page_groups.pop(page_id, None)
        self._terminal_page_widgets.pop(page_id, None)

    def _split_tab_header(self, title: str, session: TerminalSession) -> Gtk.Box:
        """Build a split-page tab header with a title and close action.

        The close button closes the terminal page through the normal grouped
        terminal close path, so all sessions belonging to that page are
        handled together.
        """
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
        """Build a terminal tab header labeled with its working directory.

        The header includes a close button connected to the session's regular
        notebook close operation.
        """
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
        """Wrap a terminal widget in a labeled, closable split pane.

        The pane header identifies the terminal's working directory, while
        the close action removes only that session from the split group.
        """
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
        """Remove one terminal pane and collapse its split when possible.

        The session is detached from its parent paned widget and reported as
        closed. If it was the final split member, the surviving terminal is
        restored to a regular notebook page; otherwise the remaining split
        tree stays in place and is selected.
        """
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
        """Save the active editor using its current or supplied destination.

        The operation delegates to :meth:`save_editor`, which also refreshes
        the tab title after saving. If the selected page is not an editor,
        there is no document to save and a ``ValueError`` is raised.

        Args:
            save_service: Service that writes the editor buffer to disk.
            path: Optional destination path for this save operation.

        Returns:
            The resolved path returned after saving the active editor.

        Raises:
            ValueError: If no editor page is currently active.
        """
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
        """Save an editor and refresh its corresponding tab label.

        The editor handles writing its buffer and updating its current path.
        This method then synchronizes the tab label with the editor's latest
        title and modified state.

        Args:
            editor: Editor panel whose buffer should be saved.
            save_service: Service responsible for writing the buffer.
            path: Optional destination path; otherwise the editor's path is used.

        Returns:
            The resolved path to which the editor was saved.
        """
        saved_path = editor.save_file(save_service, path)
        self._update_tab_label(editor)
        return saved_path

    def request_close_editor(self, editor: EditorPanel) -> None:
        """Route an editor close request to its owner or close it immediately.

        Applications that need to prompt about unsaved changes can provide a
        close-request callback. Without one, this method removes the editor
        directly through :meth:`close_editor`.
        """
        if self._on_close_requested is None:
            self.close_editor(editor)
        else:
            self._on_close_requested(editor)

    def _update_tab_label(self, editor: EditorPanel) -> None:
        """Synchronize an editor tab label with its current document state.

        The file name is used for saved documents and the editor title for
        untitled documents. An asterisk is appended while the buffer is
        modified. If the editor has no registered tab label, nothing is
        changed.
        """
        tab_label = self._tab_labels.get(id(editor))
        if tab_label is None:
            return
        title = editor.file_path.name if editor.file_path is not None else editor.title.get_text()
        tab_label.set_text(f"{title}{'*' if editor.buffer.get_modified() else ''}")

    def close_editor(self, editor: EditorPanel) -> None:
        """Remove an editor page from the notebook.

        Editors that are not pages are ignored. After removal, the label
        registration is discarded, the tab strip is hidden if the notebook
        becomes empty, and listeners are notified of the new active page.
        """
        page_number = self.page_num(editor)
        if page_number < 0:
            return

        self.remove_page(page_number)
        self._tab_labels.pop(id(editor), None)
        if self.get_n_pages() == 0:
            self.set_show_tabs(False)
        self._notify_active_changed()

    def close_terminal(self, session: TerminalSession) -> None:
        """Close the notebook page containing the requested terminal session.

        For a split page, all sessions in that page are removed from tracking
        and sent to the close callback. A standalone terminal is handled as a
        one-session group. If no matching notebook page exists, the method
        leaves the notebook unchanged.
        """
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
        """Close all currently tracked terminal sessions.

        A tuple snapshot is iterated because closing a session removes entries
        from the underlying tracking map.
        """
        for session in tuple(self._terminal_sessions.values()):
            self.close_terminal(session)

    def _on_switch_page(
        self, _notebook: Gtk.Notebook, _page: Gtk.Widget, _page_number: int
    ) -> None:
        """Forward a GTK notebook page-switch event to the active listener.

        GTK supplies the notebook, page, and index as signal arguments; the
        manager derives the current page itself before notifying its callback.
        """
        self._notify_active_changed()

    def _notify_active_changed(self) -> None:
        """Notify the optional listener about the selected notebook page.

        If no active-page callback was supplied, this operation has no side
        effects.
        """
        if self._on_active_changed is not None:
            self._on_active_changed(self.active_page)
