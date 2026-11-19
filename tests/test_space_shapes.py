import cairo
import gi
import pytest

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from codevision.shape import SHAPES
from space.color import COLOR_PALETTE
from space.shape_item import ShapeItem
from space.space_view import SpaceView


def test_shape_picker_inserts_selected_shape_with_active_color() -> None:
    space = SpaceView()
    shape_button = space.tool_buttons["Shapes"]
    assert isinstance(shape_button, Gtk.MenuButton)
    menu = shape_button.get_popover()
    expected_names = (
        "Process", "Subprocess", "Input / Output", "Terminal",
        "Predefined Process", "Manual Input", "Manual Operation",
        "Preparation", "Connector", "Off-Page Connector", "Delay", "Merge",
        "Extract", "Sort", "Stored Data", "Internal Storage", "Tape Storage",
        "Magnetic Disk", "Hard Drive", "Memory", "Cache", "API Gateway",
        "Microservice", "Client", "Web Browser", "Mobile Device",
        "Desktop Application", "Firewall", "Router", "Switch", "Network",
        "Load Generator", "Message Broker", "Event Bus", "Notification",
        "Authentication", "Authorization", "Encryption", "Monitoring",
        "Log Collector", "Arrow",
    )
    assert tuple(shape.name for shape in SHAPES) == expected_names
    assert len(menu.shape_buttons) == len(expected_names)
    assert len({shape.shape_id for shape in SHAPES}) == len(expected_names)
    assert len({type(shape).__module__ for shape in SHAPES}) == len(expected_names)
    assert all(shape.purpose for shape in SHAPES)

    color = COLOR_PALETTE[6][1]
    space.drawing_color.set(color)
    menu.shape_buttons[0].emit("clicked")

    assert len(space.shape_items) == 1
    item = space.shape_items[0]
    assert isinstance(item, ShapeItem)
    assert item.shape is SHAPES[0]
    assert item.color == color
    assert not space.tool_buttons["Pen"].get_active()
    assert not space.ink_canvas.get_can_target()


def test_shapes_render_and_work_with_board_item_actions() -> None:
    space = SpaceView()
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 160, 110)
    context = cairo.Context(surface)
    color = (0.2, 0.6, 0.9)
    for shape in SHAPES:
        shape.draw(context, 144, 96, color)

    item = space.add_shape(SHAPES[0], (100.0, 120.0), color)
    duplicate = space.duplicate_board_item(item)
    assert isinstance(duplicate, ShapeItem)
    assert duplicate.shape is item.shape
    assert duplicate.color == item.color
    assert (duplicate.x, duplicate.y) == (120.0, 140.0)

    assert space.remove_board_item(item)
    assert item not in space.shape_items
    space.clear_board()
    assert not space.shape_items


def test_shape_items_can_be_dragged_and_resized_at_zoom() -> None:
    space = SpaceView()
    item = space.add_shape(SHAPES[0], (100.0, 120.0))
    space.zoom.scale = 2.0
    space._dragged_import_item = item
    space._import_drag_origin = (item.x, item.y)

    space._on_import_drag_update(None, 40.0, 20.0)
    assert (item.x, item.y) == (120.0, 130.0)

    original_right = item.x + item.width
    original_bottom = item.y + item.height
    item._on_resize_begin(None, 0.0, 0.0, "nw")
    item._on_resize_update(None, -40.0, -20.0, "nw")

    assert (item.width, item.height) == (item.WIDTH + 20, item.HEIGHT + 10)
    assert (item.x + item.width, item.y + item.height) == (
        original_right,
        original_bottom,
    )
    item._on_resize_end(None, -40.0, -20.0, "nw")

    item._on_resize_begin(None, 0.0, 0.0, "se")
    item._on_resize_update(None, -1000.0, -1000.0, "se")
    assert item.width == item.MIN_WIDTH
    assert item.height == item.MIN_HEIGHT


def test_arrow_direction_is_adjustable_and_copied_per_item() -> None:
    space = SpaceView()
    arrow_shape = next(shape for shape in SHAPES if shape.shape_id == "arrow")
    arrow = space.add_shape(arrow_shape)

    assert arrow.direction == "right"
    assert arrow.direction_control is not None
    assert set(arrow.direction_buttons) == {"up", "right", "down", "left"}
    arrow.direction_buttons["up"].emit("clicked")
    assert arrow.direction == "up"

    rendered_directions = set()
    right_direction_image = None
    for direction in ("up", "right", "down", "left"):
        arrow.set_direction(direction)
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 144, 96)
        arrow._draw_shape(
            arrow.canvas,
            cairo.Context(surface),
            144,
            96,
        )
        surface.flush()
        image = bytes(surface.get_data())
        rendered_directions.add(image)
        if direction == "right":
            right_direction_image = image
    assert len(rendered_directions) == 4

    arrow.set_direction("right")
    arrow._on_rotation_begin(None, 0.0, 0.0)
    arrow._on_rotation_update(None, 39.0, 0.0)
    assert arrow.rotation == pytest.approx(0.78539816339)
    assert arrow.direction is None
    rotated_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 144, 96)
    arrow._draw_shape(
        arrow.canvas,
        cairo.Context(rotated_surface),
        144,
        96,
    )
    rotated_surface.flush()
    assert bytes(rotated_surface.get_data()) != right_direction_image
    arrow._on_rotation_end(None, 39.0, 0.0)

    duplicate = space.duplicate_board_item(arrow)
    assert isinstance(duplicate, ShapeItem)
    assert duplicate.rotation == pytest.approx(arrow.rotation)

    arrow.set_direction("left")
    assert arrow.direction == "left"
    assert duplicate.rotation != arrow.rotation
    with pytest.raises(ValueError):
        arrow.set_direction("diagonal")
