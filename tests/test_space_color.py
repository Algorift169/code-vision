import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from codevision.space.color import (
    COLOR_HEXES,
    COLOR_PALETTE,
    DEFAULT_COLOR,
    DrawingColor,
)
from codevision.space.pen import Pen
from codevision.space.space_view import SpaceView


def test_color_palette_has_36_unique_colors_and_defaults_to_white() -> None:
    drawing_color = DrawingColor()

    assert len(COLOR_HEXES) >= 30
    assert len(set(COLOR_HEXES)) == len(COLOR_HEXES)
    assert drawing_color.current == DEFAULT_COLOR


def test_color_popover_selection_updates_shared_pen_color() -> None:
    space = SpaceView()
    color_button = space.tool_buttons["Color"]
    assert isinstance(color_button, Gtk.MenuButton)
    palette = color_button.get_popover()
    selected_button = palette.swatch_buttons[6]

    selected_button.emit("clicked")

    selected_color = COLOR_PALETTE[6][1]
    assert space.drawing_color.current == selected_color
    assert space.pen.color == selected_color


def test_pen_strokes_keep_the_color_selected_when_drawn() -> None:
    canvas = Gtk.DrawingArea()
    canvas.set_content_width(100)
    canvas.set_content_height(100)
    drawing_color = DrawingColor()
    pen = Pen(canvas, drawing_color=drawing_color)
    pen.set_enabled(True)

    pen._on_drag_begin(None, 10.0, 10.0)
    pen._on_drag_end(None, 10.0, 0.0)
    first_color = pen.stroke_colors[0]

    drawing_color.set(COLOR_PALETTE[6][1])
    pen._on_drag_begin(None, 30.0, 30.0)
    pen._on_drag_end(None, 10.0, 0.0)

    assert first_color == DEFAULT_COLOR
    assert pen.stroke_colors == [DEFAULT_COLOR, COLOR_PALETTE[6][1]]
