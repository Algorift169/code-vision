from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Gio", "2.0")
from gi.repository import Gdk, Gio, GLib, Gtk, Pango

from ..editor.editor import EditorPanel
from ..editor.tab import EditorTabs
from ..services.auto_save import AutoSaveSettings
from ..services.save import SaveService
from ..services.terminal import TerminalService
from ..ui.analysis_panel import AnalysisPanel
from ..ui.border import WindowBorder
from ..ui.project_explorer import ProjectExplorer
from ..ui.search import WorkspaceSearch
from ..ui.theme import ThemeManager
from ..ui.widgets.edit_menu import EditMenuButton
from ..ui.widgets.file_menu import FileMenuButton
from ..ui.widgets.help_menu import HelpMenuButton
from ..ui.widgets.menu import ContextMenu
from ..ui.widgets.menu_context import MenuContext
from ..ui.widgets.terminal_menu import TerminalMenuButton
from ..ui.widgets.view_menu import ViewMenuButton


STYLESHEETS = (
    "main-window.css",
    "window-border.css",
    "headerbar.css",
    "window-controls.css",
    "panels.css",
    "project-explorer.css",
    "context-menu.css",
    "folder-picker.css",
    "editor.css",
    "editor-tabs.css",
    "analysis-panel.css",
    "kong-browser.css",
)


class CodeVisionWindow(Gtk.ApplicationWindow):
    """Main IDE-style workspace with left, center, and right panels."""

    """Initializes the main GTK window and prepares its application services.
    It then builds the header, workspace panels, editor tabs, search, and status
    bar, before connecting actions, timers, menus, and window event handlers.
    """
    def __init__(self, application: Gtk.Application) -> None:
        super().__init__(application=application)
        self.set_title("CodeVision")
        self.set_default_size(1400, 900)
        self.set_size_request(1100, 700)
        self.set_name("codevision-window")
        self.set_decorated(False)
        self.save_service = SaveService()
        self._auto_save_settings = AutoSaveSettings()
        self._auto_save_enabled = self._auto_save_settings.enabled
        self.terminal_service = TerminalService()
        self._context_menu_root: Gtk.Widget | None = None
        self._open_dialog: Gtk.FileChooserNative | None = None
        self._save_dialog: Gtk.FileChooserNative | None = None
        self._project_explorer_visible = True
        self._analysis_panel_visible = True
        self._editor_visible = True
        self._focus_mode_active = False
        self._editor_zoom = 0
        self._editor_font_providers: dict[int, Gtk.CssProvider] = {}

        self._install_css()
        self.theme_manager = ThemeManager()
        self.theme_manager.apply(self.theme_manager.current_theme)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_child(WindowBorder(box))

        header = Gtk.HeaderBar()
        header.set_show_title_buttons(False)
        header.set_hexpand(True)

        menu_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        menu_bar.add_css_class("menu-bar")
        menu_bar.set_margin_start(0)
        self.edit_menu = EditMenuButton(self)
        menu_bar.append(self.edit_menu)
        self.view_menu = ViewMenuButton(self)
        menu_bar.append(self.view_menu)
        self.terminal_menu = TerminalMenuButton(self)
        menu_bar.append(self.terminal_menu)
        for menu_name in ("Project",):
            menu_button = Gtk.MenuButton(label=menu_name)
            menu_button.add_css_class("menu-button")
            popover = Gtk.Popover()
            menu_content = Gtk.Label(label="Project menu is not implemented yet")
            menu_content.set_margin_top(10)
            menu_content.set_margin_bottom(10)
            menu_content.set_margin_start(12)
            menu_content.set_margin_end(12)
            popover.set_child(menu_content)
            menu_button.set_popover(popover)
            menu_bar.append(menu_button)
        self.help_menu = HelpMenuButton(self)
        menu_bar.append(self.help_menu)
        header.pack_start(menu_bar)

        title_search = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        title_search.set_margin_start(120)
        title = Gtk.Label(label="CodeVision")
        title.add_css_class("window-title")
        title_search.append(title)

        search = Gtk.SearchEntry()
        search.set_placeholder_text("Search anything...")
        search.add_css_class("search-entry")
        search.set_size_request(220, 11)
        title_search.append(search)
        header.set_title_widget(title_search)

        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        controls.add_css_class("window-controls")

        minimize_button = self._create_window_control("Minimize window", "minimize")
        minimize_button.connect("clicked", lambda _button: self.minimize())
        controls.append(minimize_button)

        fullscreen_button = self._create_window_control(
            "Toggle fullscreen", "fullscreen"
        )
        fullscreen_button.connect("clicked", lambda _button: self._toggle_fullscreen())
        controls.append(fullscreen_button)

        close_button = self._create_window_control("Close window", "close")
        close_button.connect("clicked", lambda _button: self.close())
        controls.append(close_button)

        header.pack_end(controls)
        box.append(header)

        workspace = Gtk.Paned.new(Gtk.Orientation.HORIZONTAL)
        workspace.set_wide_handle(True)
        workspace.set_hexpand(True)
        workspace.set_vexpand(True)
        workspace.set_shrink_start_child(False)
        workspace.set_shrink_end_child(False)

        self.workspace = workspace
        self._project_placeholder = Gtk.Box()
        self._project_placeholder.set_hexpand(True)
        self._project_placeholder.set_vexpand(True)
        self._analysis_placeholder = Gtk.Box()
        self._analysis_placeholder.set_hexpand(True)
        self._analysis_placeholder.set_vexpand(True)
        self._editor_placeholder = Gtk.Box()
        self._editor_placeholder.set_hexpand(True)
        self._editor_placeholder.set_vexpand(True)
        right_pane = Gtk.Paned.new(Gtk.Orientation.HORIZONTAL)
        right_pane.set_wide_handle(True)
        right_pane.set_shrink_start_child(False)
        right_pane.set_shrink_end_child(False)
        self.right_pane = right_pane

        welcome_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        welcome_page.set_name("welcome-page")
        welcome_page.set_hexpand(True)
        welcome_page.set_vexpand(True)
        welcome_page.set_halign(Gtk.Align.FILL)
        welcome_page.set_valign(Gtk.Align.FILL)

        welcome_message = Gtk.Label(label="Welcome to Code-Vision")
        welcome_message.set_hexpand(True)
        welcome_message.set_vexpand(True)
        welcome_message.set_halign(Gtk.Align.CENTER)
        welcome_message.set_valign(Gtk.Align.CENTER)
        welcome_message.add_css_class("welcome-message")
        welcome_page.append(welcome_message)

        self.center_stack = Gtk.Stack()
        self.center_stack.set_name("editor-stack")
        self.center_stack.set_hexpand(True)
        self.center_stack.set_vexpand(True)
        self.center_stack.set_size_request(320, -1)
        self.center_stack.add_named(welcome_page, "welcome")

        self.editor_tabs = EditorTabs(
            self._on_active_editor_changed,
            on_terminal_closed=self.terminal_service.close,
            on_close_requested=self._close_editor,
            split_terminal_factory=self.terminal_service.open,
        )
        self.center_stack.add_named(self.editor_tabs, "editor")
        self.center_stack.set_visible_child_name("welcome")
        self.file_menu = FileMenuButton(self)
        menu_bar.prepend(self.file_menu)

        """ The app icon is loaded from the resources/icons directory relative to the
        main_window.py file. If the icon file is not found, the app will still function"""
        app_icon_path = (
            Path(__file__).resolve().parents[3] / "resources" / "icons" / "cv.png"
        )
        if app_icon_path.is_file():
            app_icon = Gtk.Image.new_from_file(str(app_icon_path))
            app_icon.set_pixel_size(15)
            app_icon.set_tooltip_text("CodeVision")
            app_icon.set_valign(Gtk.Align.CENTER)
            app_icon.set_margin_end(6)
            menu_bar.prepend(app_icon)

        project_panel = ProjectExplorer(
            on_file_open=self._open_file,
            terminal_service=self.terminal_service,
        )
        self.project_explorer = project_panel
        self.workspace_search = WorkspaceSearch(
            search,
            lambda: self.project_explorer.root_path,
            self._open_file,
            self.project_explorer.reveal_path,
        )
        project_panel.set_name("project-panel")

        analysis_panel = AnalysisPanel()
        analysis_panel.set_name("analysis-panel")
        self.analysis_panel = analysis_panel

        workspace.set_start_child(project_panel)
        workspace.set_end_child(right_pane)
        workspace.set_position(260)

        right_pane.set_start_child(self.center_stack)
        right_pane.set_end_child(analysis_panel)
        right_pane.set_position(820)
        self.project_panel = project_panel

        workspace_overlay = Gtk.Overlay()
        workspace_overlay.set_hexpand(True)
        workspace_overlay.set_vexpand(True)
        workspace_overlay.set_child(workspace)
        workspace_overlay.add_overlay(self.workspace_search.results_panel)
        self.workspace_search.results_panel.set_margin_top(6)
        box.append(workspace_overlay)

        status = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        status.set_margin_start(12)
        status.set_margin_end(12)
        status.set_margin_top(8)
        status.set_margin_bottom(8)

        status_label = Gtk.Label(label="CodeVision")
        status_label.add_css_class("muted-label")
        status.append(status_label)
        self.status_label = status_label

        version = Gtk.Label(label="v0.1.0")
        version.add_css_class("muted-label")
        status.append(version)

        box.append(status)
        self._install_file_actions(application)
        self._install_edit_actions(application)
        self._auto_save_source = GLib.timeout_add_seconds(2, self._auto_save_documents)
        self._context_menu_root = box
        self.context_menu = ContextMenu(box, self._window_menu_context_at)
        self.file_menu.update_state()
        self.edit_menu.update_state()
        self.view_menu._update_state()
        self.connect("close-request", self._on_close_request)
        self._enable_edge_resize()

    """ These little functions expose the window's internal state to 
    the application for menu state updates and other logic. They are 
    used to check the visibility of the editor, project explorer, and 
    analysis panel, as well as whether focus mode is active. """
    """Reports the editor panel's current visibility state.
    The view menu uses this value to keep its toggle state consistent with the
    workspace layout.
    """
    def editor_visible(self) -> bool:
        return self._editor_visible

    """Reports whether the project explorer is currently visible.
    It returns the stored state so menu controls can reflect the left pane.
    """
    def project_explorer_visible(self) -> bool:
        return self._project_explorer_visible

    """Reports whether the analysis panel is currently visible.
    The view menu reads this state when it updates its panel controls.
    """
    def analysis_panel_visible(self) -> bool:
        return self._analysis_panel_visible

    """Reports whether focus mode is enabled for this window.
    This lets other UI components display the current mode accurately.
    """
    def focus_mode_active(self) -> bool:
        return self._focus_mode_active

    """Applies a theme by its identifier through the theme manager.
    If the view menu has already been constructed, it refreshes that menu so
    its selected-theme state matches the newly applied styling.
    """
    def set_theme(self, theme_id: str) -> None:
        self.theme_manager.apply(theme_id)
        if hasattr(self, "view_menu"):
            self.view_menu._update_state()
    """All the functions with 'toggle :
    Switches the editor between visible and hidden states, 
    toggles the project explorer and analysis panel visibility, 
    and manages focus mode, which hides both the project explorer 
    and analysis panel for a distraction-free coding experience.

    When window s hidden,it replaces the editor with a placeholder, 
    and when shown, it restores the editor. The same logic applies 
    to the project explorer and analysis panel. The focus mode 
remembers the previous visibility states of the project explorer
    and analysis panel, allowing users to return to their previous 
layout after exiting focus mode. The view menu is updated after
    each toggle to reflect the current state of the UI components.
    """
    """Switches the editor area between the real editor and a placeholder.
    It flips the stored visibility flag, swaps the pane's child to match, and
    refreshes the view menu so its control reflects the new state.
    """
    def toggle_editor_visibility(self) -> None:
        self._editor_visible = not self._editor_visible
        if self._editor_visible:
            self.right_pane.set_start_child(self.center_stack)
        else:
            self.right_pane.set_start_child(self._editor_placeholder)
        self.view_menu._update_state()

    """Switches the left workspace pane between explorer and placeholder.
    It updates the visibility flag, replaces the pane child, and refreshes the
    view menu to reflect the changed layout.
    """
    def toggle_project_explorer(self) -> None:
        self._project_explorer_visible = not self._project_explorer_visible
        if self._project_explorer_visible:
            self.workspace.set_start_child(self.project_panel)
        else:
            self.workspace.set_start_child(self._project_placeholder)
        self.view_menu._update_state()

    """Switches the right-side analysis pane between panel and placeholder.
    It updates the stored visibility flag and pane child, then refreshes the
    view menu so the toggle state stays synchronized.
    """
    def toggle_analysis_panel(self) -> None:
        self._analysis_panel_visible = not self._analysis_panel_visible
        if self._analysis_panel_visible:
            self.right_pane.set_end_child(self.analysis_panel)
        else:
            self.right_pane.set_end_child(self._analysis_placeholder)
        self.view_menu._update_state()

    """Enables a simpler workspace and restores the layout when disabled.
    On entry it remembers each side panel's visibility before hiding them; on
    exit it restores those saved states and refreshes the view menu.
    """
    def toggle_focus_mode(self) -> None:
        self._focus_mode_active = not self._focus_mode_active
        if self._focus_mode_active:
            self._focus_mode_previous_project = self._project_explorer_visible
            self._focus_mode_previous_analysis = self._analysis_panel_visible
            self.toggle_project_explorer()
            self.toggle_analysis_panel()
        else:
            self._project_explorer_visible = getattr(self, "_focus_mode_previous_project", True)
            self._analysis_panel_visible = getattr(self, "_focus_mode_previous_analysis", True)
            if self._project_explorer_visible:
                self.workspace.set_start_child(self.project_panel)
            else:
                self.workspace.set_start_child(self._project_placeholder)
            if self._analysis_panel_visible:
                self.right_pane.set_end_child(self.analysis_panel)
            else:
                self.right_pane.set_end_child(self._analysis_placeholder)
        self.view_menu._update_state()

    """Increases the editor's zoom level by one step.
    The value is capped at 8 so repeated input cannot grow the text without
    limit; the updated level is then applied to open source views.
    """
    def zoom_in(self) -> None:
        self._editor_zoom = min(self._editor_zoom + 1, 8)
        self._apply_editor_zoom()

    """Decreases the editor's zoom level by one step.
    The value is limited to -5 to keep the text from shrinking indefinitely,
    then the new font size is applied to open source views.
    """
    def zoom_out(self) -> None:
        self._editor_zoom = max(self._editor_zoom - 1, -5)
        self._apply_editor_zoom()

    """Returns editor zoom to its default level.
    It resets the stored adjustment to zero and reapplies the default font size
    to each open source view.
    """
    def reset_zoom(self) -> None:
        self._editor_zoom = 0
        self._apply_editor_zoom()

    """Applies the current zoom level as CSS to every editor source view.
    It calculates a point size, skips tabs without a source view, reuses or
    creates a CSS provider for each view, then requests a layout resize.
    """
    def _apply_editor_zoom(self) -> None:
        size = 11 + self._editor_zoom
        css = f"textview {{ font-family: 'Sans'; font-size: {size}pt; }}"
        for editor in self.editor_tabs.editors:
            if not hasattr(editor, "source_view"):
                continue
            source_view = editor.source_view
            provider = self._editor_font_providers.get(id(source_view))
            if provider is None:
                provider = Gtk.CssProvider()
                self._editor_font_providers[id(source_view)] = provider
            style_context = source_view.get_style_context()
            style_context.remove_provider(provider)
            provider.load_from_string(css)
            style_context.add_provider(provider, Gtk.STYLE_PROVIDER_PRIORITY_USER)
            source_view.queue_resize()

    """Chooses where a new terminal session should start.
    It prefers the supplied directory, falls back to the project root, and
    finally uses the process working directory before opening a terminal tab.
    """
    def new_terminal(self, directory: Path | None = None) -> None:
        target = directory or self.project_explorer.root_path or Path.cwd()
        self._open_terminal_tab(target)

    """Splits the active terminal into a second terminal pane.
    If no terminal is active it reports that in the status bar; otherwise it
    requests the split, shows the tab area, and reports completion.
    """
    def split_terminal(self) -> None:
        active = self.editor_tabs.active_terminal
        if active is None:
            self.status_label.set_text("Open a terminal before splitting it")
            return
        self.editor_tabs.split_terminal(active)
        self.center_stack.set_visible_child_name("editor")
        self.status_label.set_text("Terminal split vertically")

    """Provides a simple terminal-creation entry point for menu callers.
    It delegates directory selection and tab creation to `new_terminal`.
    """
    def create_terminal(self, directory: Path | None = None) -> None:
        self.new_terminal(directory)

    """Compiles and runs the active C or C++ file in a terminal.
    It validates the active editor and file type, opens a terminal beside the
    file, sends the generated command to its process, and updates the status.
    """
    def run_active_file(self) -> None:
        editor = self.editor_tabs.active_editor
        if editor is None or editor.file_path is None:
            self.status_label.set_text("Open a file before running it")
            return
        cmd = self._build_run_command(editor.file_path)
        if not cmd:
            self.status_label.set_text("This file type cannot be run from the terminal")
            return
        self.create_terminal(editor.file_path.parent)
        session = self.editor_tabs.active_terminal
        if session is not None and hasattr(session.terminal, "feed_child"):
            session.terminal.feed_child((cmd + "\n").encode("utf-8"))
        self.status_label.set_text(f"Running: {editor.file_path.name}")

    """Starts the project's build command in a new terminal session.
    It chooses the project root or current directory, opens a terminal there,
    sends `make` to the terminal process, and updates the status bar.
    """
    def run_build(self) -> None:
        target = self.project_explorer.root_path or Path.cwd()
        self.create_terminal(target)
        session = self.editor_tabs.active_terminal
        if session is not None and hasattr(session.terminal, "feed_child"):
            session.terminal.feed_child(b"make\n")
        self.status_label.set_text("Build started")

    """Clears the active terminal if its widget supports resetting.
    It checks for an active session and the reset operation first; if either is
    missing it reports that no terminal can be cleared.
    """
    def clear_terminal(self) -> None:
        session = self.editor_tabs.active_terminal
        if session is None or not hasattr(session.terminal, "reset"):
            self.status_label.set_text("No active terminal to clear")
            return
        session.terminal.reset(True, True)

    """Closes the active terminal session through the editor-tab manager.
    If there is no active session it reports that; otherwise it closes the tab
    and displays a termination message.
    """
    def kill_terminal(self) -> None:
        session = self.editor_tabs.active_terminal
        if session is None:
            self.status_label.set_text("No active terminal to kill")
            return
        self.editor_tabs.close_terminal(session)
        self.status_label.set_text("Terminal process terminated")

    """Displays a modal information dialog about terminal settings.
    The dialog currently explains that settings belong to the active session
    and provides a Close button; it does not edit terminal configuration.
    """
    def show_terminal_settings(self) -> None:
        dialog = Gtk.Dialog(title="Terminal Settings", transient_for=self, modal=True)
        dialog.add_button("Close", Gtk.ResponseType.CLOSE)
        content = dialog.get_content_area()
        content.set_margin_top(16)
        content.set_margin_bottom(16)
        content.set_margin_start(16)
        content.set_margin_end(16)
        content.append(Gtk.Label(label="Terminal settings are managed by the current session."))
        dialog.present()

    """Requests that the operating system open the project documentation URL.
    GTK delegates the URL to whichever browser is configured as the default.
    """
    def open_documentation(self) -> None:
        Gio.AppInfo.launch_default_for_uri("https://github.com/Algorift169/code-vision")

    """Creates and presents a modal dialog containing keyboard shortcuts.
    It adds a Close button, formats the shortcut list in a left-aligned label,
    and displays the dialog relative to this window.
    """
    def show_shortcuts_dialog(self) -> None:
        dialog = Gtk.Dialog(title="Keyboard Shortcuts", transient_for=self, modal=True)
        dialog.add_button("Close", Gtk.ResponseType.CLOSE)
        content = dialog.get_content_area()
        content.set_margin_top(16)
        content.set_margin_bottom(16)
        content.set_margin_start(16)
        content.set_margin_end(16)
        text = Gtk.Label(
            label="Save: Ctrl+S\nFind: Ctrl+F\nUndo: Ctrl+Z\nRedo: Ctrl+Y\nFull Screen: F11\nZoom In: Ctrl++\nZoom Out: Ctrl+-\nReset Zoom: Ctrl+0"
        )
        text.set_xalign(0)
        content.append(text)
        dialog.present()

    """Creates and presents a short getting-started dialog.
    The text lists basic project, editing, view, terminal, and theme actions;
    the modal dialog keeps interaction focused until it is closed.
    """
    def show_guide_dialog(self) -> None:
        dialog = Gtk.Dialog(title="CodeVision Guide", transient_for=self, modal=True)
        dialog.add_button("Close", Gtk.ResponseType.CLOSE)
        content = dialog.get_content_area()
        content.set_margin_top(16)
        content.set_margin_bottom(16)
        content.set_margin_start(16)
        content.set_margin_end(16)
        text = Gtk.Label(
            label="Getting Started\n\n- Open a folder\n- Edit files\n- Use View toggles for panels\n- Run code via Terminal\n- Use theme switching for visual styling"
        )
        text.set_xalign(0)
        content.append(text)
        dialog.present()

    """Opens the project's issue-tracker URL through the system browser.
    This delegates browser selection and URL handling to GTK's AppInfo API.
    """
    def report_issue(self) -> None:
        Gio.AppInfo.launch_default_for_uri("https://github.com/Algorift169/code-vision/issues")

    """Opens the source repository URL through the system browser.
    GTK forwards the request to the user's configured default browser.
    """
    def view_source_code(self) -> None:
        Gio.AppInfo.launch_default_for_uri("https://github.com/Algorift169/code-vision")

    """Informs the user that update checking is not implemented yet.
    It currently changes only the status message and performs no network check.
    """
    def check_for_updates(self) -> None:
        self.status_label.set_text("No update service is configured yet")

    """Creates an About dialog and fills it with CodeVision metadata.
    It sets the program name, version, description, and website, loads the app
    icon as a paintable, and presents the dialog as a modal window.
    """
    def show_about_dialog(self) -> None:
        dialog = Gtk.AboutDialog()
        dialog.set_transient_for(self)
        dialog.set_modal(True)
        dialog.set_program_name("CodeVision")
        dialog.set_version("0.1.0")
        dialog.set_comments("Code analysis and visualization workspace")
        dialog.set_website("https://github.com/Algorift169/code-vision")
        icon = Gtk.Image.new_from_file(
            str(Path(__file__).resolve().parents[3] / "resources" / "icons" / "cv.png")
        )
        """FIXED: the About dialog ow passes the image’s paintable to Gtk.
        AboutDialog.set_logo() instead of passing the Gtk.Image widget."""
        dialog.set_logo(icon.get_paintable())
        dialog.present()

    """Builds a shell command for supported source-file extensions.
    It lowercases the suffix, selects `gcc` for C or `g++` for C++, and joins
    compilation and execution with `&&`; unsupported types return an empty string.
    """
    @staticmethod
    def _build_run_command(file_path: Path) -> str:
        suffix = file_path.suffix.lower()
        if suffix == ".c":
            return f"gcc '{file_path}' -o /tmp/codevision_run && /tmp/codevision_run"
        if suffix == ".cpp":
            return f"g++ '{file_path}' -o /tmp/codevision_run && /tmp/codevision_run"
        return ""

    """Validates a path and opens the file in the editor tab collection.
    It reports directories or read errors in the status bar; on success it
    selects the editor view and displays the opened file path.
    """
    def _open_file(self, path: Path) -> None:
        if not path.is_file():
            self.status_label.set_text("Only files can be opened in the editor")
            return

        try:
            editor = self.editor_tabs.open_file(path)
        except OSError as error:
            self.status_label.set_text(f"Could not open {path.name}: {error}")
            return

        self.center_stack.set_visible_child_name("editor")
        self.status_label.set_text(str(editor.file_path))

    """Provides read-only access to this window's auto-save setting.
    The property returns the stored flag without changing the setting or
    triggering a save operation.
    """
    @property
    def auto_save_enabled(self) -> bool:
        return self._auto_save_enabled

    """Starts the project explorer's existing new-file workflow.
    It activates the explorer's GTK action so file creation stays owned by
    the component that manages project files.
    """
    def new_file(self) -> None:
        self.project_explorer.new_file_action.activate()

    """Adds a blank, untitled text document to the editor tabs.
    It gives the document a display title, leaves its language unspecified,
    and switches the center stack from the welcome page to the editor.
    """
    def new_text_file(self) -> None:
        self.editor_tabs.new_document("Untitled Text", language_id=None)
        self.center_stack.set_visible_child_name("editor")

    """Creates a browser tab and optionally navigates to a requested URL.
    It selects the editor area and then reports the browser's current address,
    using a new-tab label when the browser has no current URL.
    """
    def open_kong_browser(self, target_url: str | None = None) -> None:
        browser = self.editor_tabs.open_kong_browser(target_url)
        if target_url is not None:
            browser.load_url(target_url)
        self.center_stack.set_visible_child_name("editor")
        self.status_label.set_text(f"Kong Browser: {browser.service.current_url or 'new tab'}")

    """Creates another CodeVision window attached to this GTK application.
    It first verifies that the application is a Gtk.Application, then constructs
    and presents a fresh window using the same application instance.
    """
    def new_window(self) -> None:
        application = self.get_application()
        if isinstance(application, Gtk.Application):
            window = CodeVisionWindow(application)
            window.present()

    """Shows the native file chooser used to select a file to open.
    If a chooser is already active it re-shows that dialog; otherwise it creates
    one, connects its response handler, stores it, and presents it.
    """
    def open_file_dialog(self) -> None:
        if self._open_dialog is not None:
            self._open_dialog.show()
            return

        dialog = Gtk.FileChooserNative.new(
            "Open File", self, Gtk.FileChooserAction.OPEN, "_Open", "_Cancel"
        )
        dialog.connect("response", self._on_open_file_response)
        self._open_dialog = dialog
        dialog.show()

    """Saves the active document using its current path when possible.
    It does nothing without an active editor, opens Save As for an untitled
    document, and delegates existing-path saves to `_save_editor`.
    """
    def save_current_file(self) -> None:
        editor = self.editor_tabs.active_editor
        if editor is None:
            return
        if editor.file_path is None:
            self._show_save_dialog(editor)
        else:
            self._save_editor(editor)

    """Requests a destination path for the active editor's document.
    It only opens the dialog when an editor is active; the response handler
    performs the actual save after the user chooses a path.
    """
    def save_file_as(self) -> None:
        editor = self.editor_tabs.active_editor
        if editor is not None:
            self._show_save_dialog(editor)

    """Saves the active document to a separate copy chosen by the user.
    It opens the shared save-dialog flow with copy mode enabled, leaving the
    editor's original file path unchanged.
    """
    def share_current_file(self) -> None:
        editor = self.editor_tabs.active_editor
        if editor is not None:
            self._show_save_dialog(editor, share_copy=True)

    """Changes auto-save preference and synchronizes every open app window.
    It persists the preference, updates each CodeVision window's flag and menu,
    then displays the new setting in this window's status bar.
    """
    def set_auto_save(self, enabled: bool) -> None:
        self._auto_save_settings.set_enabled(enabled)
        application = self.get_application()
        windows = application.get_windows() if isinstance(application, Gtk.Application) else [self]
        for window in windows:
            if isinstance(window, CodeVisionWindow):
                window._auto_save_enabled = enabled
                window.file_menu.update_state()
        self.status_label.set_text(f"Auto Save {'On' if enabled else 'Off'}")

    """Asks the shared close handler to close the active editor.
    The handler closes clean documents immediately and prompts before discarding
    any modified document.
    """
    def close_active_editor(self) -> None:
        editor = self.editor_tabs.active_editor
        if editor is not None:
            self._close_editor(editor)

    """Reverses the latest edit in the active editor when one exists.
    After delegating undo to the editor, it refreshes the edit menu's enabled
    state to match the editor's updated history.
    """
    def undo(self) -> None:
        editor = self.editor_tabs.active_editor
        if editor is not None:
            editor.undo()
            self.edit_menu.update_state()

    """Reapplies the next undone edit in the active editor when available.
    It delegates the operation to the editor and then refreshes edit-menu state.
    """
    def redo(self) -> None:
        editor = self.editor_tabs.active_editor
        if editor is not None:
            editor.redo()
            self.edit_menu.update_state()

    """Removes the active editor's selected text and places it on the clipboard.
    The editor performs the cut; the window then refreshes the edit menu state.
    """
    def cut(self) -> None:
        editor = self.editor_tabs.active_editor
        if editor is not None:
            editor.cut()
            self.edit_menu.update_state()

    """Copies the active editor's selected text to the clipboard.
    If an editor exists it delegates the copy operation and refreshes the edit
    menu so its available commands reflect the current selection.
    """
    def copy(self) -> None:
        editor = self.editor_tabs.active_editor
        if editor is not None:
            editor.copy()
            self.edit_menu.update_state()

    """Inserts clipboard content into the active editor when one exists.
    The editor handles the paste operation, after which the edit menu state is
    refreshed to reflect the changed document.
    """
    def paste(self) -> None:
        editor = self.editor_tabs.active_editor
        if editor is not None:
            editor.paste()
            self.edit_menu.update_state()

            """Checks for an active editor before reporting Find availability.
            The search operation itself is not implemented here; this method currently
            only updates the status bar when an editor is open.
            """
    def find(self) -> None:
        editor = self.editor_tabs.active_editor
        if editor is None:
            return
        self.status_label.set_text("Find is available in the active editor")

    """Checks for an active editor before reporting Replace availability.
    Actual text replacement is not performed in this method; it currently
    communicates availability through the status bar.
    """
    def replace(self) -> None:
        editor = self.editor_tabs.active_editor
        if editor is None:
            return
        self.status_label.set_text("Replace is available in the active editor")

    """Reports that the workspace-wide search entry point is ready.
    It currently sets a status message and does not itself scan project files.
    """
    def find_in_files(self) -> None:
        self.status_label.set_text("Find in Files is ready for workspace search")

    """Reports that workspace-wide replacement is ready to use.
    It currently changes only the status message; file replacement logic is
    handled elsewhere or is not yet implemented here.
    """
    def replace_in_files(self) -> None:
        self.status_label.set_text("Replace in Files is ready for workspace replacement")

    """Asks the active editor to comment or uncomment its current line.
    When an editor exists, it delegates the text change and refreshes the edit
    menu to reflect the resulting editor state.
    """
    def toggle_line_comment(self) -> None:
        editor = self.editor_tabs.active_editor
        if editor is not None:
            editor.toggle_line_comment()
            self.edit_menu.update_state()

    """Asks the active editor to comment or uncomment a selected block.
    It does nothing without an active editor; after delegation it refreshes the
    edit menu state.
    """
    def toggle_block_comment(self) -> None:
        editor = self.editor_tabs.active_editor
        if editor is not None:
            editor.toggle_block_comment()
            self.edit_menu.update_state()

    """Asks the active editor to expand an abbreviation at the cursor.
    If there is no editor it returns immediately; if expansion fails it reports
    that result, and then refreshes the edit menu state.
    """
    def expand_abbreviation(self) -> None:
        editor = self.editor_tabs.active_editor
        if editor is None:
            return
        if not editor.expand_abbreviation():
            self.status_label.set_text("No expandable abbreviation was found")
        self.edit_menu.update_state()

    """Processes the user's response to the native Open dialog.
    On acceptance it extracts a local path and delegates opening to `_open_file`;
    regardless of the response, it destroys the dialog and clears its reference.
    """
    def _on_open_file_response(
        self, dialog: Gtk.FileChooserNative, response: int
    ) -> None:
        if response == Gtk.ResponseType.ACCEPT:
            selected = dialog.get_file()
            path = selected.get_path() if selected is not None else None
            if path is None:
                self.status_label.set_text("Choose a local file to open")
            else:
                self._open_file(Path(path))
        dialog.destroy()
        self._open_dialog = None

    """Finds the widget under the pointer and selects the matching menu context.
    It checks the project tree, editor, terminal, and empty project area in turn,
    translating coordinates where needed before delegating context creation.
    """
    def _window_menu_context_at(self, x: float, y: float) -> MenuContext:
        root = self._context_menu_root
        if root is None:
            return self._generic_menu_context()

        target = root.pick(x, y, Gtk.PickFlags.DEFAULT)
        tree = self.project_explorer.tree
        if target is not None and self._is_within(target, tree):
            translated = root.translate_coordinates(tree, x, y)
            if translated is not None:
                tree_x, tree_y = translated
                return self._attach_terminal_action(
                    self.project_explorer.menu_context_at(tree_x, tree_y)
                )

        editor = self.editor_tabs.active_editor
        if editor is not None and target is not None and self._is_within(
            target, editor.source_view
        ):
            translated = root.translate_coordinates(editor.source_view, x, y)
            if translated is not None:
                editor_x, editor_y = translated
                return self._attach_terminal_action(
                    self._editor_menu_context_at(editor, editor_x, editor_y)
                )
        terminal_session = self.editor_tabs.active_terminal
        if (
            terminal_session is not None
            and target is not None
            and self._is_within(target, terminal_session.terminal)
        ):
            context = self._generic_menu_context(target)
            context.kind = "terminal"
            context.terminal_widget = terminal_session.terminal
            context.close_terminal_tab = lambda: self.editor_tabs.close_terminal(
                terminal_session
            )
            return self._attach_terminal_action(context)
        if target is not None and self._is_within(target, self.project_explorer.content):
            return self._attach_terminal_action(
                self.project_explorer.empty_menu_context()
            )
        return self._generic_menu_context(target)

    """Adds window-level operations that can be used by a context menu.
    The callbacks open a terminal in the context directory or open the browser;
    the theme manager is also attached before the context is returned.
    """
    def _attach_terminal_action(self, context: MenuContext) -> MenuContext:
        context.open_terminal = lambda: self._open_terminal_tab(context.directory)
        context.open_kong_browser = lambda target_url=None: self.open_kong_browser(target_url)
        context.theme_manager = self.theme_manager
        return context

    """Creates a fallback menu context for the window or a selected widget.
    It chooses the project root or current directory and packages shared services
    and callbacks for file creation, terminals, browser tabs, and status updates.
    """
    def _generic_menu_context(
        self, target: Gtk.Widget | None = None
    ) -> MenuContext:
        directory = self.project_explorer.root_path or Path.cwd()
        return MenuContext(
            widget=target or self,
            kind="window",
            project_root=self.project_explorer.root_path,
            terminal_service=self.terminal_service,
            theme_manager=self.theme_manager,
            open_terminal=lambda: self._open_terminal_tab(directory),
            open_kong_browser=lambda target_url=None: self.open_kong_browser(target_url),
            create_file=lambda: self.project_explorer.create_file_in(directory),
            on_files_pasted=self.project_explorer._refresh_pasted_files,
            set_status=self.status_label.set_text,
        )

    """Tests whether a GTK widget is the given ancestor or one of its descendants.
    Starting at the target, it repeatedly follows `get_parent()`; it returns
    true when the requested ancestor is reached and false at the top of the tree.
    """
    @staticmethod
    def _is_within(widget: Gtk.Widget, ancestor: Gtk.Widget) -> bool:
        current: Gtk.Widget | None = widget
        while current is not None:
            if current is ancestor:
                return True
            current = current.get_parent()
        return False

    """Collects editor-specific values needed by a right-click menu.
    It chooses the file's folder (or project/current folder), reads selected text
    when present, and packages the editor, services, and callbacks in a context.
    """
    def _editor_menu_context_at(self, editor: EditorPanel, _x: float, _y: float) -> MenuContext:
        directory = (
            editor.file_path.parent
            if editor.file_path is not None
            else self.project_explorer.root_path or Path.cwd()
        )
        selected_text = None
        if editor.source_view is not None:
            buffer = editor.source_view.get_buffer()
            bounds = buffer.get_selection_bounds()
            if bounds:
                selected_text = buffer.get_text(bounds[0], bounds[1], True)
        return MenuContext(
            widget=editor.source_view,
            kind="editor",
            path=editor.file_path,
            selected_text=selected_text,
            project_root=self.project_explorer.root_path,
            editor_view=editor.source_view,
            terminal_service=self.terminal_service,
            open_terminal=lambda: self._open_terminal_tab(directory),
            open_kong_browser=lambda target_url=None: self.open_kong_browser(target_url),
            create_file=lambda: self.project_explorer.create_file_in(directory),
            on_files_pasted=self.project_explorer._refresh_pasted_files,
            set_status=self.status_label.set_text,
        )

    """Synchronizes the center page and status bar with the active tab.
    It distinguishes editor, terminal, and empty states, then refreshes file and
    edit menus when those menu objects have already been initialized.
    """
    def _on_active_editor_changed(self, page: Gtk.Widget | None) -> None:
        if isinstance(page, EditorPanel):
            self.center_stack.set_visible_child_name("editor")
            self.status_label.set_text(str(page.file_path or page.title.get_text()))
        else:
            terminal = self.editor_tabs.active_terminal
            if terminal is not None:
                self.center_stack.set_visible_child_name("editor")
                self.status_label.set_text(f"Terminal: {terminal.directory}")
            elif page is None:
                self.center_stack.set_visible_child_name("welcome")
                self.status_label.set_text("CodeVision")
        if hasattr(self, "file_menu"):
            self.file_menu.update_state()
        if hasattr(self, "edit_menu"):
            self.edit_menu.update_state()

    """Creates the window's file actions and assigns keyboard accelerators.
    It pairs action names with methods, connects each GTK action to its callback,
    adds actions to the window, then registers shortcuts such as Ctrl+S.
    """
    def _install_file_actions(self, application: Gtk.Application) -> None:
        actions: tuple[tuple[str, Callable[[], None]], ...] = (
            ("new-file", self.new_file),
            ("open-file", self.open_file_dialog),
            ("save", self.save_current_file),
            ("save-as", self.save_file_as),
            ("close-editor", self.close_active_editor),
        )
        for name, callback in actions:
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", lambda _action, _parameter, cb=callback: cb())
            self.add_action(action)

        for action_name, accelerators in (
            ("new-file", ["<Primary>n"]),
            ("open-file", ["<Primary>o"]),
            ("save", ["<Primary>s"]),
            ("save-as", ["<Primary><Shift>s"]),
            ("close-editor", ["<Primary>w"]),
        ):
            application.set_accels_for_action(f"win.{action_name}", accelerators)

    """Creates the editing actions and binds their keyboard accelerators.
    It registers editor commands as window actions, connects them to methods,
    and associates shortcuts such as Ctrl+Z and Ctrl+F with those action names.
    """
    def _install_edit_actions(self, application: Gtk.Application) -> None:
        actions: tuple[tuple[str, Callable[[], None]], ...] = (
            ("undo", self.undo),
            ("redo", self.redo),
            ("cut", self.cut),
            ("copy", self.copy),
            ("paste", self.paste),
            ("find", self.find),
            ("replace", self.replace),
            ("find-in-files", self.find_in_files),
            ("replace-in-files", self.replace_in_files),
            ("toggle-line-comment", self.toggle_line_comment),
            ("toggle-block-comment", self.toggle_block_comment),
            ("expand-abbreviation", self.expand_abbreviation),
        )
        for name, callback in actions:
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", lambda _action, _parameter, cb=callback: cb())
            self.add_action(action)

        for action_name, accelerators in (
            ("undo", ["<Primary>z"]),
            ("redo", ["<Primary>y"]),
            ("cut", ["<Primary>x"]),
            ("copy", ["<Primary>c"]),
            ("paste", ["<Primary>v"]),
            ("find", ["<Primary>f"]),
            ("replace", ["<Primary>h"]),
            ("find-in-files", ["<Primary><Shift>f"]),
            ("replace-in-files", ["<Primary><Shift>h"]),
            ("toggle-line-comment", ["<Primary>slash"]),
            ("toggle-block-comment", ["<Primary><Shift>a"]),
            ("expand-abbreviation", ["Tab"]),
        ):
            application.set_accels_for_action(f"win.{action_name}", accelerators)

    """Creates a native Save dialog for a document that needs a destination.
    It reuses an existing dialog if one is open; otherwise it sets the title and
    suggested filename, connects the response callback, stores, and displays it.
    """
    def _show_save_dialog(
        self,
        editor: EditorPanel,
        on_saved: Callable[[], None] | None = None,
        *,
        share_copy: bool = False,
    ) -> None:
        if self._save_dialog is not None:
            self._save_dialog.show()
            return

        title = "Share a Copy" if share_copy else "Save File As"
        dialog = Gtk.FileChooserNative.new(
            title, self, Gtk.FileChooserAction.SAVE, "_Save", "_Cancel"
        )
        dialog.set_do_overwrite_confirmation(True)
        dialog.set_current_name(
            editor.file_path.name
            if editor.file_path is not None
            else editor.title.get_text()
        )
        dialog.connect(
            "response", self._on_save_dialog_response, editor, on_saved, share_copy
        )
        self._save_dialog = dialog
        dialog.show()

    """Handles an accepted Save dialog and releases the dialog afterward.
    It extracts the selected local path, saves either a copy or the editor, and
    runs the optional follow-up only after a successful normal save.
    """
    def _on_save_dialog_response(
        self,
        dialog: Gtk.FileChooserNative,
        response: int,
        editor: EditorPanel,
        on_saved: Callable[[], None] | None,
        share_copy: bool,
    ) -> None:
        if response == Gtk.ResponseType.ACCEPT:
            selected = dialog.get_file()
            raw_path = selected.get_path() if selected is not None else None
            if raw_path is None:
                self.status_label.set_text("Choose a local file path")
            elif share_copy:
                try:
                    self.save_service.save_file(Path(raw_path), self._editor_text(editor))
                    self.status_label.set_text("A local copy was saved")
                except OSError as error:
                    self.status_label.set_text(f"Could not create a copy: {error}")
            elif self._save_editor(editor, Path(raw_path)) and on_saved is not None:
                on_saved()

        dialog.destroy()
        self._save_dialog = None

    """Saves an editor document to its current path or an optional new path.
    It rejects a missing existing file, delegates the write to the tab manager
    and save service, catches expected errors, and returns whether saving worked.
    """
    def _save_editor(self, editor: EditorPanel, path: Path | None = None) -> bool:
        if path is None and editor.file_path is not None and not editor.file_path.is_file():
            self.status_label.set_text("File no longer exists; use Save As to choose a path")
            return False
        try:
            saved_path = self.editor_tabs.save_editor(editor, self.save_service, path)
        except (OSError, ValueError) as error:
            self.status_label.set_text(f"Could not save document: {error}")
            return False

        self.status_label.set_text(f"Saved {saved_path}")
        return True

    """Returns the complete text stored in an editor's text buffer.
    It obtains the start and end iterators from the buffer bounds, then asks GTK
    for the text between those positions, including hidden characters.
    """
    @staticmethod
    def _editor_text(editor: EditorPanel) -> str:
        start, end = EditorPanel._bounds_as_iters(editor.buffer.get_bounds())
        return editor.buffer.get_text(start, end, True)

    """Closes an editor safely while protecting modified document contents.
    Clean documents close immediately; modified ones get a modal prompt offering
    cancel, discard, or save before the editor tab is removed.
    """
    def _close_editor(self, editor: EditorPanel) -> None:
        if not editor.buffer.get_modified():
            self.editor_tabs.close_editor(editor)
            return

        dialog = Gtk.Dialog(title="Unsaved Changes", transient_for=self, modal=True)
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("Don't Save", Gtk.ResponseType.REJECT)
        dialog.add_button("Save", Gtk.ResponseType.ACCEPT)
        dialog.set_default_response(Gtk.ResponseType.ACCEPT)
        content = dialog.get_content_area()
        content.set_margin_top(16)
        content.set_margin_bottom(16)
        content.set_margin_start(16)
        content.set_margin_end(16)
        content.append(Gtk.Label(label=f"Save changes to {editor.title.get_text()}?"))

        """Applies the user's choice from the unsaved-changes prompt.
        It closes without saving on discard, starts Save As for untitled files,
        and closes a named file only after `_save_editor` reports success.
        """
        def on_response(_dialog: Gtk.Dialog, response: int) -> None:
            dialog.close()
            if response == Gtk.ResponseType.REJECT:
                self.editor_tabs.close_editor(editor)
            elif response == Gtk.ResponseType.ACCEPT:
                if editor.file_path is None:
                    self._show_save_dialog(
                        editor, on_saved=lambda: self.editor_tabs.close_editor(editor)
                    )
                elif self._save_editor(editor):
                    self.editor_tabs.close_editor(editor)

        dialog.connect("response", on_response)
        dialog.present()

    """Periodically saves modified documents while auto-save is enabled.
    It visits open editor tabs, skips untitled or unchanged documents, delegates
    each eligible save, and returns GLib's value for repeating the timer.
    """
    def _auto_save_documents(self) -> bool:
        if self._auto_save_enabled:
            for editor in self.editor_tabs.editors:
                if editor.file_path is not None and editor.buffer.get_modified():
                    self._save_editor(editor)
        return GLib.SOURCE_CONTINUE

    """Releases recurring and child resources as the window is closing.
    It removes the auto-save timer, closes workspace search and terminal tabs,
    shuts down the terminal service, then allows GTK to continue closing.
    """
    def _on_close_request(self, _window: Gtk.Window) -> bool:
        GLib.source_remove(self._auto_save_source)
        self.workspace_search.close()
        self.editor_tabs.close_all_terminals()
        self.terminal_service.close_all()
        return False

    """Asks the terminal service to start a session in the requested directory.
    It reports startup errors in the status bar; on success it adds the session
    as an editor tab and switches the center area to show that tab.
    """
    def _open_terminal_tab(self, directory: Path) -> None:
        try:
            session = self.terminal_service.open(directory)
        except (OSError, RuntimeError, ValueError) as error:
            self.status_label.set_text(str(error))
            return
        self.editor_tabs.open_terminal(session)
        self.center_stack.set_visible_child_name("editor")

    """Builds one custom button for the undecorated window header.
    It applies a tooltip, fixed size, vertical alignment, and shared plus
    control-specific CSS classes, then returns the button for signal wiring.
    """
    def _create_window_control(
        self, tooltip: str, color_class: str
    ) -> Gtk.Button:
        button = Gtk.Button()
        button.set_tooltip_text(tooltip)
        button.set_size_request(16, 10)
        button.set_valign(Gtk.Align.CENTER)
        button.add_css_class("window-control")
        button.add_css_class(color_class)
        return button

    """Toggles the window between fullscreen and its previous windowed state.
    It checks GTK's current fullscreen state and calls the matching transition.
    """
    def _toggle_fullscreen(self) -> None:
        if self.is_fullscreen():
            self.unfullscreen()
        else:
            self.fullscreen()

    """Installs pointer controllers needed to resize a borderless window.
    The drag controller starts native resizing at an edge; the motion controller
    updates the cursor to show which resize direction is available.
    """
    def _enable_edge_resize(self) -> None:
        drag = Gtk.GestureDrag.new()
        drag.set_button(1)
        drag.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        drag.connect("drag-begin", self._on_resize_drag_begin)
        self.add_controller(drag)

        motion = Gtk.EventControllerMotion.new()
        motion.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        motion.connect("motion", self._on_resize_motion)
        motion.connect("leave", lambda *_args: self.set_cursor(None))
        self.add_controller(motion)

    """Starts a GTK toplevel resize when a drag begins near the window border.
    It finds the edge and surface first, denies the gesture when resizing is not
    possible, and otherwise passes the event device and coordinates to GTK.
    """
    def _on_resize_drag_begin(
        self, gesture: Gtk.GestureDrag, start_x: float, start_y: float
    ) -> None:
        edge = self._resize_edge_at(start_x, start_y)
        surface = self.get_surface()
        if edge is None or surface is None or not isinstance(surface, Gdk.Toplevel):
            gesture.set_state(Gtk.EventSequenceState.DENIED)
            return

        surface.begin_resize(
            edge,
            gesture.get_current_event_device(),
            gesture.get_current_button(),
            start_x,
            start_y,
            gesture.get_current_event_time(),
        )
        gesture.set_state(Gtk.EventSequenceState.CLAIMED)

    """Updates the pointer cursor to match the nearest resizable edge.
    It ignores motion not belonging to this window, maps the pointer to an edge,
    then selects the matching cursor or clears it when no edge is nearby.
    """
    def _on_resize_motion(
        self, controller: Gtk.EventControllerMotion, x: float, y: float
    ) -> None:
        if controller.get_widget() is not self:
            return

        edge = self._resize_edge_at(x, y)
        cursors = {
            Gdk.SurfaceEdge.NORTH_WEST: "nw-resize",
            Gdk.SurfaceEdge.NORTH: "n-resize",
            Gdk.SurfaceEdge.NORTH_EAST: "ne-resize",
            Gdk.SurfaceEdge.WEST: "w-resize",
            Gdk.SurfaceEdge.EAST: "e-resize",
            Gdk.SurfaceEdge.SOUTH_WEST: "sw-resize",
            Gdk.SurfaceEdge.SOUTH: "s-resize",
            Gdk.SurfaceEdge.SOUTH_EAST: "se-resize",
        }
        if edge is None:
            self.set_cursor(None)
        else:
            self.set_cursor_from_name(cursors[edge])

    """Determines whether coordinates fall within the window's resize border.
    It returns no edge in fullscreen; otherwise it tests an 8-pixel margin and
    returns the matching side or corner, with corners checked before sides.
    """
    def _resize_edge_at(self, x: float, y: float) -> Gdk.SurfaceEdge | None:
        
        """A fullscreen window has no usable resize border, 
        so the method exits immediately"""
        if self.is_fullscreen():
            return None

        """Now Check whether the pointer is within 8 pixels of each side:
        Here, x and y are the pointer’s coordinates inside the window.
        Each variable becomes True when the pointer is near that side.
        """
        border = 8
        left = x < border
        right = x >= self.get_width() - border
        top = y < border
        bottom = y >= self.get_height() - border

        """then Check corners before sides:
        A pointer near two sides at once is in a corner.
        The method checks all four corners first, so a top-left 
        position returns the northwest corner rather than just the top 
        or left edge.
        """
        if top and left:
            return Gdk.SurfaceEdge.NORTH_WEST
        if top and right:
            return Gdk.SurfaceEdge.NORTH_EAST
        if bottom and left:
            return Gdk.SurfaceEdge.SOUTH_WEST
        if bottom and right:
            return Gdk.SurfaceEdge.SOUTH_EAST
        if top:
            return Gdk.SurfaceEdge.NORTH
        if bottom:
            return Gdk.SurfaceEdge.SOUTH
        if left:
            return Gdk.SurfaceEdge.WEST
        if right:
            return Gdk.SurfaceEdge.EAST
            """This means the pointer is inside the 
            window, outside the 8-pixel resize border."""
        return None


    """Loads the window's stylesheets and registers them with the GTK display.
    It exits if no display exists, locates the styles directory with a working-
    directory fallback, then loads each listed file into a retained CSS provider.
    """
    def _install_css(self) -> None:
        display = Gdk.Display.get_default()
        if display is None:
            return

        styles_dir = Path(__file__).resolve().parents[3] / "resources" / "styles"
        if not styles_dir.is_dir():
            styles_dir = Path.cwd() / "resources" / "styles"

        self._css_providers = []
        for stylesheet in STYLESHEETS:
            provider = Gtk.CssProvider()
            provider.load_from_path(str(styles_dir / stylesheet))
            Gtk.StyleContext.add_provider_for_display(display,provider,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )
            self._css_providers.append(provider)
