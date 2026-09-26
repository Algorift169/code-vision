from __future__ import annotations

from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gtk

from .analysis_panel import AnalysisPanel
from .editor import EditorPanel
from .project_tree import ProjectTreePanel


STYLESHEETS = (
    "main-window.css",
    "headerbar.css",
    "window-controls.css",
    "panels.css",
    "project-explorer.css",
    "editor.css",
    "analysis-panel.css",
)


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
        menu_bar.set_margin_start(60)
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
        self._enable_edge_resize()

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

    def _toggle_fullscreen(self) -> None:
        if self.is_fullscreen():
            self.unfullscreen()
        else:
            self.fullscreen()

    def _enable_edge_resize(self) -> None:
        drag = Gtk.GestureDrag.new()
        drag.set_button(1)
        drag.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        drag.connect("drag-begin", self._on_resize_drag_begin)
        self.add_controller(drag)

        motion = Gtk.EventControllerMotion.new()
        motion.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        motion.connect("motion", self._on_resize_motion)
        motion.connect("leave", lambda _controller: self.set_cursor(None))
        self.add_controller(motion)

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

    def _on_resize_motion(
        self, _controller: Gtk.EventControllerMotion, x: float, y: float
    ) -> None:
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

    def _resize_edge_at(self, x: float, y: float) -> Gdk.SurfaceEdge | None:
        if self.is_fullscreen():
            return None

        border = 8
        left = x < border
        right = x >= self.get_width() - border
        top = y < border
        bottom = y >= self.get_height() - border

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
        return None

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
            Gtk.StyleContext.add_provider_for_display(
                display,
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )
            self._css_providers.append(provider)
