from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import cairo
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Pango", "1.0")
from gi.repository import Gtk, Pango

from . import SHAPES
from .base import DiagramShape

if TYPE_CHECKING:
    from space.color import DrawingColor


class ShapeMenu(Gtk.Popover):
    """Themed shape picker with live previews in the current drawing color."""

    def __init__(
        self,
        drawing_color: DrawingColor,
        on_select: Callable[[DiagramShape], None],
    ) -> None:
        super().__init__()
        self.drawing_color = drawing_color
        self.on_select = on_select
        self.previews: list[Gtk.DrawingArea] = []
        self.shape_buttons: list[Gtk.Button] = []
        self.set_position(Gtk.PositionType.BOTTOM)
        self.set_autohide(True)
        self.add_css_class("space-shape-popover")

        grid = Gtk.Grid()
        grid.set_row_spacing(4)
        grid.set_column_spacing(4)
        grid.add_css_class("space-shape-grid")

        for index, shape in enumerate(SHAPES):
            button = Gtk.Button()
            button.add_css_class("space-shape-option")
            button.set_tooltip_text(f"{shape.name}: {shape.purpose}")

            content = Gtk.Box(
                orientation=Gtk.Orientation.VERTICAL,
                spacing=2,
            )
            preview = Gtk.DrawingArea()
            preview.set_content_width(54)
            preview.set_content_height(38)
            preview.set_draw_func(self._draw_preview, shape)
            preview.set_can_target(False)
            label = Gtk.Label(label=shape.name)
            label.set_ellipsize(Pango.EllipsizeMode.END)
            content.append(preview)
            content.append(label)
            button.set_child(content)
            button.connect("clicked", self._on_shape_clicked, shape)
            grid.attach(button, index % 4, index // 4, 1, 1)
            self.previews.append(preview)
            self.shape_buttons.append(button)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        content.set_margin_start(8)
        content.set_margin_end(8)
        content.set_margin_top(8)
        content.set_margin_bottom(8)
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_propagate_natural_height(True)
        scroller.set_max_content_height(440)
        scroller.set_min_content_width(320)
        scroller.set_child(grid)
        content.append(scroller)
        self.set_child(content)
        drawing_color.subscribe(self._on_color_changed)

    def _on_shape_clicked(
        self,
        _button: Gtk.Button,
        shape: DiagramShape,
    ) -> None:
        self.on_select(shape)
        self.popdown()

    def _on_color_changed(self, _color: tuple[float, float, float]) -> None:
        for preview in self.previews:
            preview.queue_draw()

    def _draw_preview(
        self,
        _area: Gtk.DrawingArea,
        context: cairo.Context,
        width: int,
        height: int,
        shape: DiagramShape,
    ) -> None:
        context.translate(4, 4)
        shape.draw(
            context,
            max(1, width - 8),
            max(1, height - 8),
            self.drawing_color.current,
        )
