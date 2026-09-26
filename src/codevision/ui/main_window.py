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
}

.search-entry {
    background: #12243d;
    color: #dfeafc;
    border-radius: 8px;
    border: 1px solid #1d3556;
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

        self._install_css()

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_child(box)

        header = Gtk.HeaderBar()
        header.set_title_widget(Gtk.Label(label="CodeVision"))
        header.set_show_title_buttons(True)
        header.set_hexpand(True)
        self.set_titlebar(header)

        search = Gtk.SearchEntry()
        search.set_placeholder_text("Search anything...")
        search.add_css_class("search-entry")
        search.set_size_request(220, 28)
        header.pack_end(search)

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
