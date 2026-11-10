from pathlib import Path

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
gi.require_version("GtkSource", "5")
from gi.repository import Gdk, Gtk, GtkSource

from codevision.ui.widgets.edit_menu import EditMenuButton
from codevision.ui.widgets.file_menu import FileMenuButton
from codevision.ui.widgets.help_menu import HelpMenuButton
from codevision.ui.widgets.menu import ContextMenu
from codevision.ui.widgets.menu_actions import (
    copy,
    kill_terminal,
    paste,
    select,
    select_all,
)
from codevision.ui.widgets.menu_actions.copy_full_path import full_path
from codevision.ui.widgets.menu_actions.copy_relative_path import relative_path
from codevision.ui.widgets.menu_actions.paste import copy_files_to_directory
from codevision.ui.widgets.menu_context import MenuContext
from codevision.ui.widgets.project_menu import ProjectMenuButton
from codevision.ui.widgets.terminal_menu import TerminalMenuButton
from codevision.ui.widgets.view_menu import ViewMenuButton


def test_project_menu_vision_opens_analysis_panel() -> None:
    opened: list[bool] = []

    class DummyWindow:
        def __init__(self) -> None:
            self.content_overlay = Gtk.Overlay()

        def show_analysis_panel(self) -> None:
            opened.append(True)

    window = DummyWindow()
    menu = ProjectMenuButton(window, window.content_overlay)

    assert menu._items["vision"].get_label() == "Vision"
    menu.popup()
    menu._items["vision"].emit("clicked")

    assert opened == [True]
    assert not menu.get_active()


class SelectionWidget:
    def __init__(self) -> None:
        self.focused = False
        self.all_selected = False
        self.has_selection = True
        self.copy_count = 0
        self.paste_count = 0

    def grab_focus(self) -> None:
        self.focused = True

    def select_all(self) -> None:
        self.all_selected = True

    def get_has_selection(self) -> bool:
        return self.has_selection

    def copy_clipboard(self) -> None:
        self.copy_count += 1

    def paste_clipboard(self) -> None:
        self.paste_count += 1


class EditorBufferView:
    def __init__(self, buffer: GtkSource.Buffer) -> None:
        self._buffer = buffer

    def get_buffer(self) -> GtkSource.Buffer:
        return self._buffer

    def get_editable(self) -> bool:
        return True


def test_context_menu_is_an_overlay_widget_without_a_popover_grab() -> None:
    overlay = Gtk.Overlay()
    content = Gtk.Box()
    overlay.set_child(content)
    context_menu = ContextMenu(
        overlay,
        content,
        lambda _x, _y: MenuContext(widget=content, kind="window"),
    )

    assert context_menu.get_parent() is overlay
    assert isinstance(context_menu, Gtk.Box)
    assert not isinstance(context_menu, Gtk.Popover)
    assert not context_menu.get_visible()


def test_context_menu_action_icons_use_theme_accent_class() -> None:
    overlay = Gtk.Overlay()
    content = Gtk.Box()
    overlay.set_child(content)
    context_menu = ContextMenu(
        overlay,
        content,
        lambda _x, _y: MenuContext(widget=content, kind="window"),
    )

    for action_id in (
        "new-file",
        "open-terminal",
        "change-theme",
        "kong-browser",
    ):
        button = context_menu._items[action_id][0]
        row = button.get_child()
        icon = row.get_first_child()
        assert isinstance(icon, Gtk.DrawingArea)
        assert icon.has_css_class("context-menu-icon")
        assert icon.get_content_width() == 18
        assert icon.get_content_height() == 18
        assert icon.get_size_request() == (18, 18)


def test_terminal_menu_actions_have_visible_icon_widgets() -> None:
    class DummyWindow:
        content_overlay = Gtk.Overlay()

        def __getattr__(self, _name):
            return lambda *args, **kwargs: None

    menu = TerminalMenuButton(DummyWindow(), DummyWindow.content_overlay)
    buttons = [
        child
        for child in menu._content
        if isinstance(child, Gtk.Button)
    ]

    assert buttons
    for button in buttons:
        row = button.get_child()
        icon = row.get_first_child()
        assert isinstance(icon, Gtk.DrawingArea)
        assert icon.has_css_class("terminal-menu-icon")
        assert icon.get_content_width() == 18
        assert icon.get_content_height() == 18
        assert icon.get_size_request() == (18, 18)


def test_context_menu_dismissal_hides_overlay_without_popup_state() -> None:
    overlay = Gtk.Overlay()
    content = Gtk.Box()
    overlay.set_child(content)
    context_menu = ContextMenu(
        overlay,
        content,
        lambda _x, _y: MenuContext(widget=content, kind="window"),
    )

    context_menu._on_pressed(None, 1, 20, 30)
    assert context_menu.get_visible()

    context_menu._on_dismiss_pressed(None, 1, 40, 50)

    assert not context_menu.get_visible()


def test_dismiss_is_noop_when_menu_already_hidden() -> None:
    overlay = Gtk.Overlay()
    content = Gtk.Box()
    overlay.set_child(content)
    context_menu = ContextMenu(
        overlay,
        content,
        lambda _x, _y: MenuContext(widget=content, kind="window"),
    )

    assert not context_menu.get_visible()
    # Dismissing while already hidden must not raise or change state.
    context_menu._on_dismiss_pressed(None, 1, 40, 50)
    assert not context_menu.get_visible()


def test_escape_key_dismisses_visible_context_menu() -> None:
    overlay = Gtk.Overlay()
    content = Gtk.Box()
    overlay.set_child(content)
    context_menu = ContextMenu(
        overlay,
        content,
        lambda _x, _y: MenuContext(widget=content, kind="window"),
    )

    context_menu._on_pressed(None, 1, 20, 30)
    assert context_menu.get_visible()

    handled = context_menu._on_key_pressed(None, Gdk.KEY_Escape, 0, Gdk.ModifierType(0))
    assert handled is True
    assert not context_menu.get_visible()


def test_escape_key_ignored_when_menu_hidden() -> None:
    overlay = Gtk.Overlay()
    content = Gtk.Box()
    overlay.set_child(content)
    context_menu = ContextMenu(
        overlay,
        content,
        lambda _x, _y: MenuContext(widget=content, kind="window"),
    )

    handled = context_menu._on_key_pressed(None, Gdk.KEY_Escape, 0, Gdk.ModifierType(0))
    assert handled is False
    assert not context_menu.get_visible()


def test_path_copy_actions_resolve_paths_with_spaces(tmp_path: Path) -> None:
    root = tmp_path / "project with spaces"
    file_path = root / "source files" / "main file.py"
    file_path.parent.mkdir(parents=True)
    file_path.touch()
    context = MenuContext(
        widget=None,
        kind="explorer",
        path=file_path,
        project_root=root,
    )

    assert full_path(context) == file_path.resolve()
    assert relative_path(context) == Path("source files/main file.py")


def test_relative_path_rejects_paths_outside_project(tmp_path: Path) -> None:
    root = tmp_path / "project"
    outside = tmp_path / "outside.py"
    root.mkdir()
    outside.touch()
    context = MenuContext(
        widget=None,
        kind="explorer",
        path=outside,
        project_root=root,
    )

    assert relative_path(context) is None


def test_file_paste_copies_files_and_directories_with_spaces(tmp_path: Path) -> None:
    source_root = tmp_path / "source files"
    source_root.mkdir()
    source_file = source_root / "main file.py"
    source_file.write_text("print('hello')", encoding="utf-8")
    source_folder = source_root / "folder with spaces"
    source_folder.mkdir()
    (source_folder / "nested.txt").write_text("nested", encoding="utf-8")
    destination = tmp_path / "destination"
    destination.mkdir()

    copied = copy_files_to_directory([source_file, source_folder], destination)

    assert copied == [destination / source_file.name, destination / source_folder.name]
    assert copied[0].read_text(encoding="utf-8") == "print('hello')"
    assert (copied[1] / "nested.txt").read_text(encoding="utf-8") == "nested"


def test_select_actions_are_enabled_and_work_in_terminal_context() -> None:
    terminal = SelectionWidget()
    context = MenuContext(
        widget=terminal,
        kind="terminal",
        terminal_widget=terminal,
    )

    assert select.is_enabled(context)
    assert select_all.is_enabled(context)
    select.run(context)
    select_all.run(context)
    assert terminal.focused
    assert terminal.all_selected


def test_select_actions_remain_enabled_in_generic_context() -> None:
    widget = SelectionWidget()
    context = MenuContext(widget=widget, kind="window")

    assert select.is_enabled(context)
    assert select_all.is_enabled(context)
    select.run(context)
    select_all.run(context)
    assert widget.focused


def test_terminal_copy_and_paste_use_native_clipboard_actions() -> None:
    terminal = SelectionWidget()
    context = MenuContext(
        widget=terminal,
        kind="terminal",
        terminal_widget=terminal,
    )

    assert copy.is_enabled(context)
    assert paste.is_enabled(context)
    copy.run(context)
    paste.run(context)
    assert terminal.copy_count == 1
    assert terminal.paste_count == 1


def test_terminal_copy_requires_a_text_selection() -> None:
    terminal = SelectionWidget()
    terminal.has_selection = False
    context = MenuContext(
        widget=terminal,
        kind="terminal",
        terminal_widget=terminal,
    )

    assert not copy.is_enabled(context)
    copy.run(context)
    assert terminal.copy_count == 0


def test_kill_terminal_closes_the_terminal_tab() -> None:
    closed: list[bool] = []
    context = MenuContext(
        widget=None,
        kind="terminal",
        close_terminal_tab=lambda: closed.append(True),
    )

    assert kill_terminal.is_enabled(context)
    kill_terminal.run(context)
    assert closed == [True]


def test_kill_terminal_is_disabled_outside_terminal_tabs() -> None:
    context = MenuContext(widget=None, kind="window")

    assert not kill_terminal.is_enabled(context)


def test_editor_copy_and_paste_available_after_select_all() -> None:
    buffer = GtkSource.Buffer()
    buffer.set_text("selected editor text")
    editor_view = EditorBufferView(buffer)
    context = MenuContext(
        widget=editor_view,
        kind="editor",
        editor_view=editor_view,
    )

    select_all.run(context)

    assert context.has_text_selection
    assert copy.is_enabled(context)
    assert paste.is_enabled(context)


def test_explorer_copy_enabled_for_multiple_selected_paths(tmp_path: Path) -> None:
    paths = (tmp_path / "first file.txt", tmp_path / "second file.txt")
    context = MenuContext(
        widget=None,
        kind="explorer",
        selected_paths=paths,
    )

    assert copy.is_enabled(context)
    provider = copy.file_list_provider(paths)
    assert provider.ref_formats().contain_gtype(Gdk.FileList.__gtype__)


def test_close_all_menus_does_not_hide_menu_buttons() -> None:
    class DummyWindow:
        def __init__(self) -> None:
            self.content_overlay = Gtk.Overlay()
            box = Gtk.Box()
            self.content_overlay.set_child(box)
            self.context_menu = ContextMenu(
                self.content_overlay, box, lambda _x, _y: MenuContext(widget=box, kind="window")
            )
            self.editor_tabs = None
            self.file_menu = FileMenuButton(self, self.content_overlay)
            self.edit_menu = EditMenuButton(self, self.content_overlay)
            self.view_menu = ViewMenuButton(self, self.content_overlay)
            self.project_menu = ProjectMenuButton(self, self.content_overlay)
            self.terminal_menu = TerminalMenuButton(self, self.content_overlay)
            self.help_menu = HelpMenuButton(self, self.content_overlay)

        def __getattr__(self, name: str):
            return lambda *args, **kwargs: None

        def close_all_menus(self, except_menu: object | None = None) -> bool:
            from codevision.app.main_window import CodeVisionWindow
            return CodeVisionWindow.close_all_menus(self, except_menu=except_menu)

    win = DummyWindow()

    # All buttons should start visible
    buttons = [win.file_menu, win.edit_menu, win.view_menu, win.project_menu, win.terminal_menu, win.help_menu]
    for btn in buttons:
        assert btn.get_visible()

    # Opening file menu should popup file menu dropdown
    win.file_menu.popup()
    assert win.file_menu.get_active()
    assert win.file_menu.popup_widget.get_visible()

    # Closing all menus must pop down the dropdown popup but MUST NOT hide the button
    win.close_all_menus()
    assert not win.file_menu.get_active()
    assert not win.file_menu.popup_widget.get_visible()

    for btn in buttons:
        assert btn.get_visible(), f"Button {btn.get_label()} was hidden by close_all_menus!"

    # Every overlay menu button must popup and popdown without calling Gtk.Accessible.update_state
    for btn in buttons:
        btn.popup()
        assert btn.get_active()
        btn.popdown()
        assert not btn.get_active()


def test_zoom_actions_adjust_editor_zoom_level() -> None:
    from codevision.app.main_window import CodeVisionWindow

    class MinimalWindow:
        def __init__(self) -> None:
            self._editor_zoom = 0
            self._editor_font_providers = {}
            self.view_menu = MinimalViewMenu()
            self.editor_tabs = MinimalEditorTabs()

        def zoom_in(self) -> None:
            CodeVisionWindow.zoom_in(self)

        def zoom_out(self) -> None:
            CodeVisionWindow.zoom_out(self)

        def reset_zoom(self) -> None:
            CodeVisionWindow.reset_zoom(self)

        def _apply_editor_zoom(self) -> None:
            CodeVisionWindow._apply_editor_zoom(self)

    class MinimalViewMenu:
        def _update_state(self) -> None:
            pass

    class MinimalEditorTabs:
        editors = ()
        pages = ()

        def get_n_pages(self) -> int:
            return len(self.pages)

        def get_nth_page(self, page_num: int):
            return self.pages[page_num]

    class MinimalBrowser:
        def __init__(self) -> None:
            self.zoom_levels = []

        def set_zoom_level(self, zoom: float) -> None:
            self.zoom_levels.append(zoom)

    class MinimalPage:
        def __init__(self) -> None:
            self._browser = MinimalBrowser()

    win = MinimalWindow()
    page = MinimalPage()
    win.editor_tabs.pages = (page,)
    win.zoom_in()
    assert win._editor_zoom == 1
    assert page._browser.zoom_levels == []
    win.zoom_out()
    assert win._editor_zoom == 0
    win.zoom_out()
    assert win._editor_zoom == -1
    win.reset_zoom()
    assert win._editor_zoom == 0
