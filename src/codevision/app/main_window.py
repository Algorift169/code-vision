from __future__ import annotations

from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Gio", "2.0")
from gi.repository import Gdk, Gio, Gtk

from ..editor.editor import EditorPanel
from ..editor.tab import EditorTabs
from ..services.save import SaveService
from ..ui.analysis_panel import AnalysisPanel
from ..ui.border import WindowBorder
from ..ui.project_explorer import ProjectExplorer


STYLESHEETS = (
    "main-window.css",
    "window-border.css",
    "headerbar.css",
    "window-controls.css",
    "panels.css",
    "project-explorer.css",
    "folder-picker.css",
    "editor.css",
    "editor-tabs.css",
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
        self.save_service = SaveService()
        self._save_dialog: Gtk.FileChooserNative | None = None

        self._install_css()

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_child(WindowBorder(box))

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
        workspace.set_shrink_start_child(False)
        workspace.set_shrink_end_child(False)

        right_pane = Gtk.Paned.new(Gtk.Orientation.HORIZONTAL)
        right_pane.set_wide_handle(True)
        right_pane.set_shrink_start_child(False)
        right_pane.set_shrink_end_child(False)

        welcome_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        welcome_page.set_name("welcome-page")
        welcome_page.set_hexpand(True)
        welcome_page.set_vexpand(True)
        welcome_page.set_halign(Gtk.Align.FILL)
        welcome_page.set_valign(Gtk.Align.FILL)

        welcome_message = Gtk.Label(label="Welcome to Code Vision")
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

        self.editor_tabs = EditorTabs(self._on_active_editor_changed)
        self.center_stack.add_named(self.editor_tabs, "editor")
        self.center_stack.set_visible_child_name("welcome")

        project_panel = ProjectExplorer(on_file_open=self._open_file)
        project_panel.set_name("project-panel")

        analysis_panel = AnalysisPanel()
        analysis_panel.set_name("analysis-panel")

        workspace.set_start_child(project_panel)
        workspace.set_end_child(right_pane)
        workspace.set_position(260)

        right_pane.set_start_child(self.center_stack)
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
        self.status_label = status_label

        version = Gtk.Label(label="v0.1.0")
        version.add_css_class("muted-label")
        status.append(version)

        box.append(status)
        save_action = Gio.SimpleAction.new("save", None)
        save_action.connect("activate", self._on_save_action)
        self.add_action(save_action)
        application.set_accels_for_action("win.save", ["<Primary>s"])
        self._enable_edge_resize()

    def _open_file(self, path: Path) -> None:
        try:
            editor = self.editor_tabs.open_file(path)
        except OSError as error:
            self.status_label.set_text(f"Could not open {path.name}: {error}")
            return

        self.center_stack.set_visible_child_name("editor")
        self.status_label.set_text(str(editor.file_path))

    def _on_active_editor_changed(self, editor: EditorPanel | None) -> None:
        if editor is None:
            self.center_stack.set_visible_child_name("welcome")
            self.status_label.set_text("CodeVision")
            return

        self.center_stack.set_visible_child_name("editor")
        self.status_label.set_text(str(editor.file_path or editor.title.get_text()))

    def _on_save_action(
        self, _action: Gio.SimpleAction, _parameter: object | None
    ) -> None:
        editor = self.editor_tabs.active_editor
        if editor is None:
            return

        if editor.file_path is not None:
            self._save_to_path(editor.file_path)
            return

        dialog = Gtk.FileChooserNative.new(
            "Save File As",
            self,
            Gtk.FileChooserAction.SAVE,
            "_Save",
            "_Cancel",
        )
        dialog.set_current_name("Untitled")
        dialog.connect("response", self._on_save_as_response)
        self._save_dialog = dialog
        dialog.show()

    def _on_save_as_response(
        self, dialog: Gtk.FileChooserNative, response: int
    ) -> None:
        if response == Gtk.ResponseType.ACCEPT:
            selected = dialog.get_file()
            path = selected.get_path() if selected is not None else None
            if path is not None:
                self._save_to_path(Path(path))
            else:
                self.status_label.set_text("Choose a local file path to save")

        dialog.destroy()
        self._save_dialog = None

    def _save_to_path(self, path: Path) -> None:
        try:
            saved_path = self.editor_tabs.save_active(self.save_service, path)
        except OSError as error:
            self.status_label.set_text(f"Could not save {path.name}: {error}")
            return

        self.status_label.set_text(f"Saved {saved_path}")

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
        motion.connect("leave", lambda *_args: self.set_cursor(None))
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
