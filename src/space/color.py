from __future__ import annotations

from collections.abc import Callable
import math

import cairo
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk


Color = tuple[float, float, float]
DEFAULT_COLOR: Color = (1.0, 1.0, 1.0)
COLOR_HEXES = (
    "#FFFFFF", "#D9D9D9", "#A6A6A6", "#737373", "#404040", "#000000",
    "#FF3B30", "#FF6B6B", "#C62828", "#8E0000", "#E91E63", "#F8BBD0",
    "#FF9800", "#FFB74D", "#EF6C00", "#A84300", "#FFC107", "#FFF3CD",
    "#FFEB3B", "#FFF176", "#C0CA33", "#827717", "#CDDC39", "#F0F4C3",
    "#4CAF50", "#81C784", "#2E7D32", "#00695C", "#00BFA5", "#B2DFDB",
    "#00BCD4", "#80DEEA", "#03A9F4", "#1E88E5", "#3F51B5", "#9C27B0",
)


def _rgb_from_hex(hex_color: str) -> Color:
    return (
        int(hex_color[1:3], 16) / 255,
        int(hex_color[3:5], 16) / 255,
        int(hex_color[5:7], 16) / 255,
    )


COLOR_PALETTE: tuple[tuple[str, Color], ...] = tuple(
    (hex_color, _rgb_from_hex(hex_color)) for hex_color in COLOR_HEXES
)


class DrawingColor:
    """Shared current color used by Space drawing tools."""

    def __init__(self) -> None:
        self.current = DEFAULT_COLOR
        self._listeners: list[Callable[[Color], None]] = []

    def set(self, color: Color) -> None:
        if len(color) != 3 or any(not 0.0 <= component <= 1.0 for component in color):
            raise ValueError("Drawing colors must contain three RGB values from 0 to 1.")
        if color == self.current:
            return
        self.current = color
        for listener in tuple(self._listeners):
            listener(color)

    def subscribe(self, listener: Callable[[Color], None]) -> None:
        self._listeners.append(listener)
        listener(self.current)


class ColorPalette(Gtk.Popover):
    """Compact popover for selecting a shared drawing color."""

    def __init__(self, drawing_color: DrawingColor) -> None:
        super().__init__()
        self.drawing_color = drawing_color
        self.swatch_areas: list[Gtk.DrawingArea] = []
        self.swatch_buttons: list[Gtk.Button] = []
        self.set_position(Gtk.PositionType.BOTTOM)
        self.set_autohide(True)
        self.add_css_class("space-color-popover")

        grid = Gtk.Grid()
        grid.set_row_spacing(4)
        grid.set_column_spacing(4)
        grid.add_css_class("space-color-grid")

        for index, (hex_color, color) in enumerate(COLOR_PALETTE):
            button = Gtk.Button()
            button.set_tooltip_text(hex_color)
            button.add_css_class("space-color-swatch")
            area = Gtk.DrawingArea()
            area.set_content_width(22)
            area.set_content_height(22)
            area.set_draw_func(self._draw_swatch, (hex_color, color))
            button.set_child(area)
            button.connect("clicked", self._on_swatch_clicked, color)
            grid.attach(button, index % 6, index // 6, 1, 1)
            self.swatch_areas.append(area)
            self.swatch_buttons.append(button)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        content.set_margin_start(8)
        content.set_margin_end(8)
        content.set_margin_top(8)
        content.set_margin_bottom(8)
        content.append(grid)
        self.set_child(content)
        drawing_color.subscribe(self._on_color_changed)

    def _on_swatch_clicked(self, _button: Gtk.Button, color: Color) -> None:
        self.drawing_color.set(color)
        self.popdown()

    def _on_color_changed(self, _color: Color) -> None:
        for area in self.swatch_areas:
            area.queue_draw()

    def _draw_swatch(
        self,
        _area: Gtk.DrawingArea,
        context: cairo.Context,
        width: int,
        height: int,
        swatch: tuple[str, Color],
    ) -> None:
        hex_color, color = swatch
        x, y = width / 2, height / 2
        radius = min(width, height) * 0.36
        context.arc(x, y, radius, 0, 2 * math.pi)
        context.set_source_rgb(*color)
        context.fill_preserve()
        context.set_source_rgb(0.35, 0.35, 0.35)
        context.set_line_width(1)
        context.stroke()

        if color == self.drawing_color.current:
            selected_radius = radius + 3
            context.arc(x, y, selected_radius, 0, 2 * math.pi)
            if hex_color in ("#000000", "#404040", "#737373", "#8E0000"):
                context.set_source_rgb(1, 1, 1)
            else:
                context.set_source_rgb(0.15, 0.15, 0.15)
            context.set_line_width(2)
            context.stroke()
