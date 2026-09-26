from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gtk

from .analysis_panel import AnalysisPanel
from .editor import EditorPanel
from .project_tree import ProjectTreePanel


CSS = """
window {
    background-color: #071421;
    color: #e5edf8;
}

headerbar {
    background-color: #0b1830;
    color: #e5edf8;
    border-bottom: 1px solid #1a2c48;
    min-height: 11px;
    padding: 0 3px;
}

.app-name {
    color: #e5edf8;
    font-weight: 700;
    font-size: 10px;
    margin-right: 4px;
}

.menu-bar {
    background: transparent;
}

.menu-button {
    background: transparent;
    color: #c8d5e7;
    border: 0;
    border-radius: 4px;
    min-height: 11px;
    padding: 0 4px;
    font-size: 10px;
}

.menu-button:hover {
    background: #1a2d46;
}

.window-controls {
    background: transparent;
}

.window-control {
    min-width: 9px;
    min-height: 5px;
    padding: 0;
    border: 0;
    border-radius: 3px;
}

.window-control.close {
    background: #f15b5b;
}

.window-control.fullscreen {
    background: #40c879;
}

.window-control.minimize {
    background: #f4c24e;
}

.search-entry {
    background: #12243d;
    color: #dfeafc;
    border-radius: 8px;
    border: 1px solid #1d3556;
    min-height: 11px;
    padding: 0 3px;
    font-size: 10px;
}

.panel {
    background-color: #0d1a2a;
    border: 1px solid #1a2d46;
    border-radius: 8px;
}

.panel-header {
    background: transparent;
    padding: 0 0 6px;
}

.section-title {
    color: #e8eef9;
    font-weight: 700;
}

.muted-label {
    color: #9db5d4;
    font-size: 12px;
}

.card {
    background-color: rgba(19, 34, 52, 0.85);
    border: 1px solid #1a2d46;
    border-radius: 10px;
    padding: 12px;
}

.card-title {
    color: #edf4ff;
    font-weight: 700;
}

.metric-value {
    color: #dfeafc;
    font-weight: 600;
}

#project-panel, #editor-panel, #analysis-panel {
    background: #0d1a2a;
}

#code-editor {
    background-color: #0b1628;
    color: #dfeafc;
    border: 0;
    caret-color: #dfeafc;
}

#code-editor text {
    background-color: #0b1628;
    color: #dfeafc;
}

#code-editor gutter,
#code-editor gutter line-numbers {
    background-color: #0b1628;
    color: #7f91a8;
}

#code-editor selection {
    background-color: #284f7a;
}

scrolledwindow {
    background: transparent;
}

treeview {
    background: transparent;
    color: #dfeafc;
}

textview {
    background: #0b1628;
    color: #dfeafc;
}
"""


class CodeVisionWindow(Gtk.ApplicationWindow):
    """Main IDE-style workspace with left, center, and right panels."""

    def __init__(self, application: Gtk.Application) -> None:
        super().__init__(application=application)
        self.set_title("CodeVision")
        self.set_default_size(1400, 900)
        self.set_size_request(1100, 700)
        self.set_name("codevision-window")
        self.set_decorated(False)

        self._install_css()

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_child(box)

        header = Gtk.HeaderBar()
        header.set_show_title_buttons(False)
        header.set_hexpand(True)

        menu_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        menu_bar.add_css_class("menu-bar")
        app_name = Gtk.Label(label="CodeVision")
        app_name.add_css_class("app-name")
        menu_bar.append(app_name)
        for menu_name in ("File", "Edit", "View", "Analyze", "Project", "Help"):
            menu_button = Gtk.MenuButton(label=menu_name)
            menu_button.add_css_class("menu-button")
            popover = Gtk.Popover()
            menu_content = Gtk.Label(label="No actions yet")
            menu_content.set_margin_top(10)
            menu_content.set_margin_bottom(10)
            menu_content.set_margin_start(12)
            menu_content.set_margin_end(12)
            popover.set_child(menu_content)
            menu_button.set_popover(popover)
            menu_bar.append(menu_button)
        header.pack_start(menu_bar)

        search = Gtk.SearchEntry()
        search.set_placeholder_text("Search anything...")
        search.add_css_class("search-entry")
        search.set_size_request(160, 11)

        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        controls.add_css_class("window-controls")
        controls.append(search)

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

        project_panel = ProjectTreePanel()
        project_panel.set_name("project-panel")

        right_pane = Gtk.Paned.new(Gtk.Orientation.HORIZONTAL)
        right_pane.set_wide_handle(True)

        editor_panel = EditorPanel()
        editor_panel.set_name("editor-panel")

        analysis_panel = AnalysisPanel()
        analysis_panel.set_name("analysis-panel")

        workspace.set_start_child(project_panel)
        workspace.set_end_child(right_pane)
        workspace.set_position(260)

        right_pane.set_start_child(editor_panel)
        right_pane.set_end_child(analysis_panel)
        right_pane.set_position(820)

        box.append(workspace)

        status = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        status.set_margin_start(12)
        status.set_margin_end(12)
        status.set_margin_top(8)
        status.set_margin_bottom(8)

        status_label = Gtk.Label(label="CodeVision")
        status_label.add_css_class("muted-label")
        status.append(status_label)

        version = Gtk.Label(label="v0.1.0")
        version.add_css_class("muted-label")
        status.append(version)

        box.append(status)

    def _create_window_control(
        self, tooltip: str, color_class: str
    ) -> Gtk.Button:
        button = Gtk.Button()
        button.set_tooltip_text(tooltip)
        button.set_size_request(9, 5)
        button.set_valign(Gtk.Align.CENTER)
        button.add_css_class("window-control")
        button.add_css_class(color_class)
        return button

    def _toggle_fullscreen(self) -> None:
        if self.is_fullscreen():
            self.unfullscreen()
        else:
            self.fullscreen()

    def _install_css(self) -> None:
        provider = Gtk.CssProvider()
        provider.load_from_string(CSS)
        display = Gdk.Display.get_default()
        if display is not None:
            Gtk.StyleContext.add_provider_for_display(
                display,
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )
