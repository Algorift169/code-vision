from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from .eraser import Eraser
from .pen import Pen
from .rendo import Redo
from .undo import Undo


_SPACE_TOOLS = (
    ("Pen", "Draw freehand"),
    ("Undo", "Undo the last board action"),
    ("Redo", "Redo the last undone board action"),
    ("Eraser", "Erase small portions of strokes"),
    ("Box", "Add a box"),
    ("Color", "Choose a drawing color"),
    ("Text Box", "Add a text box"),
    ("Import", "Import content"),
    ("Shapes", "Choose a shape"),
    ("Zoom In", "Zoom in"),
    ("Zoom Out", "Zoom out"),
    ("Export", "Export board content"),
)


class SpaceView(Gtk.Box):
    """Workspace shell for the Analysis Panel's Space board."""

    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.set_name("space-view")
        self.set_hexpand(True)
        self.set_vexpand(True)
        self.set_margin_start(4)
        self.set_margin_end(4)
        self.set_margin_top(4)
        self.set_margin_bottom(4)

        self.toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        self.toolbar.add_css_class("space-toolbar")

        self.tool_buttons: dict[str, Gtk.Button] = {}
        for label, tooltip in _SPACE_TOOLS:
            if label in ("Pen", "Eraser"):
                button = Gtk.ToggleButton(label=label)
            else:
                button = Gtk.Button(label=label)
            button.set_tooltip_text(tooltip)
            button.add_css_class("theme-toolbar-button")
            button.add_css_class("space-tool-button")
            self.toolbar.append(button)
            self.tool_buttons[label] = button

        self.toolbar_scroller = Gtk.ScrolledWindow()
        self.toolbar_scroller.set_policy(
            Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER
        )
        self.toolbar_scroller.set_hexpand(True)
        self.toolbar_scroller.set_child(self.toolbar)
        self.append(self.toolbar_scroller)

        self.canvas_scroller = Gtk.ScrolledWindow()
        self.canvas_scroller.set_policy(
            Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC
        )
        self.canvas_scroller.set_hexpand(True)
        self.canvas_scroller.set_vexpand(True)

        self.canvas = Gtk.DrawingArea()
        self.canvas.set_name("space-canvas")
        self.canvas.set_hexpand(True)
        self.canvas.set_vexpand(True)
        self.canvas.add_css_class("space-canvas")
        self.pen = Pen(self.canvas, self._update_history_buttons)
        self.eraser = Eraser(self.pen)
        self.undo_action = Undo(self.pen)
        self.redo_action = Redo(self.pen)
        self.tool_buttons["Undo"].connect(
            "clicked", lambda _button: self.undo_action.execute()
        )
        self.tool_buttons["Redo"].connect(
            "clicked", lambda _button: self.redo_action.execute()
        )
        pen_button = self.tool_buttons["Pen"]
        pen_button.connect("toggled", self._on_pen_toggled)
        eraser_button = self.tool_buttons["Eraser"]
        eraser_button.connect("toggled", self._on_eraser_toggled)
        self._update_history_buttons()
        self.canvas_scroller.set_child(self.canvas)
        self.append(self.canvas_scroller)

        self._canvas_width = 0
        self._canvas_height = 0
        self._extending_canvas = False
        self.canvas_scroller.connect("map", self._initialize_scrollable_canvas)

    def _on_pen_toggled(self, button: Gtk.ToggleButton) -> None:
        if button.get_active() and self.tool_buttons["Eraser"].get_active():
            self.tool_buttons["Eraser"].set_active(False)
        self.pen.set_enabled(button.get_active())

    def _on_eraser_toggled(self, button: Gtk.ToggleButton) -> None:
        if button.get_active() and self.tool_buttons["Pen"].get_active():
            self.tool_buttons["Pen"].set_active(False)
        self.eraser.set_enabled(button.get_active())

    def _update_history_buttons(self) -> None:
        self.tool_buttons["Undo"].set_sensitive(self.pen.can_undo)
        self.tool_buttons["Redo"].set_sensitive(self.pen.can_redo)

    def _initialize_scrollable_canvas(self, _scroller: Gtk.ScrolledWindow) -> None:
        horizontal = self.canvas_scroller.get_hadjustment()
        vertical = self.canvas_scroller.get_vadjustment()
        horizontal.connect(
            "value-changed", self._extend_canvas_for_scroll, "width"
        )
        horizontal.connect("changed", self._extend_canvas_for_scroll, "width")
        vertical.connect(
            "value-changed", self._extend_canvas_for_scroll, "height"
        )
        vertical.connect("changed", self._extend_canvas_for_scroll, "height")
        self._extend_canvas_to_page(horizontal, "width")
        self._extend_canvas_to_page(vertical, "height")

    def _extend_canvas_for_scroll(
        self, adjustment: Gtk.Adjustment, dimension: str
    ) -> None:
        if self._extending_canvas:
            return
        page_size = int(adjustment.get_page_size())
        if page_size <= 0:
            return
        extent = self._canvas_width if dimension == "width" else self._canvas_height
        if extent == 0 or adjustment.get_upper() - adjustment.get_value() <= (
            page_size * 1.25
        ):
            self._set_canvas_extent(dimension, extent + page_size)

    def _extend_canvas_to_page(
        self, adjustment: Gtk.Adjustment, dimension: str
    ) -> None:
        page_size = int(adjustment.get_page_size())
        if page_size > 0:
            self._set_canvas_extent(dimension, page_size * 2)

    def _set_canvas_extent(self, dimension: str, extent: int) -> None:
        self._extending_canvas = True
        if dimension == "width":
            self._canvas_width = extent
            self.canvas.set_content_width(extent)
        else:
            self._canvas_height = extent
            self.canvas.set_content_height(extent)
        self._extending_canvas = False
