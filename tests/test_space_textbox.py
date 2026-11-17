import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from codevision.ui.analysis_panel import AnalysisPanel
from space.color import DrawingColor
from space.textbox import TextBox
from space.zoom import SpaceZoom


def _tag_names_at(text_box: TextBox, offset: int) -> set[str]:
    iterator = text_box.buffer.get_iter_at_offset(offset)
    return {tag.get_property("name") for tag in iterator.get_tags()}


def test_textbox_typing_keeps_different_colors_in_one_box() -> None:
    board = Gtk.Fixed()
    drawing_color = DrawingColor()
    text_box = TextBox(
        board,
        drawing_color,
        SpaceZoom(lambda: None),
        (20.0, 30.0),
        lambda _text_box: None,
        lambda _text_box: None,
        lambda _text_box: None,
    )
    buffer = text_box.buffer

    buffer.insert(buffer.get_start_iter(), "A")
    white_tag = "space-text-FFFFFF"
    assert white_tag in _tag_names_at(text_box, 0)

    red = (0.9, 0.1, 0.1)
    drawing_color.set(red)
    buffer.insert(buffer.get_end_iter(), "B")
    red_tag = "space-text-E61A1A"
    assert red_tag in _tag_names_at(text_box, 1)
    assert white_tag in _tag_names_at(text_box, 0)

    buffer.select_range(buffer.get_start_iter(), buffer.get_iter_at_offset(1))
    text_box.apply_color_to_selection((0.1, 0.2, 0.9))
    assert "space-text-1A33E6" in _tag_names_at(text_box, 0)
    assert red_tag in _tag_names_at(text_box, 1)


def test_textbox_corner_resizing_updates_position_and_size() -> None:
    board = Gtk.Fixed()
    text_box = TextBox(
        board,
        DrawingColor(),
        SpaceZoom(lambda: None),
        (40.0, 50.0),
        lambda _text_box: None,
        lambda _text_box: None,
        lambda _text_box: None,
    )
    original_width, original_height = text_box.width, text_box.height

    text_box._on_resize_begin(None, 0.0, 0.0, "nw")
    text_box._on_resize_update(None, -20.0, -10.0, "nw")

    assert text_box.x == 20.0
    assert text_box.y == 40.0
    assert text_box.width == original_width + 20
    assert text_box.height == original_height + 10
    assert "editing" in text_box.get_css_classes()

    text_box._on_resize_end(None, -20.0, -10.0, "nw")
    assert text_box._resize_corner is None
    assert "editing" not in text_box.get_css_classes()
    assert not any(handle.get_visible() for handle in text_box.handles.values())
    assert not text_box.move_handle.get_visible()


def test_space_can_create_multiple_overlapping_textboxes() -> None:
    panel = AnalysisPanel()
    space = panel._section_placeholders["Space"]
    space.tool_buttons["Text Box"].set_active(True)

    space._on_canvas_pressed(None, 1, 120.0, 80.0)
    assert not space.tool_buttons["Text Box"].get_active()
    space.tool_buttons["Text Box"].set_active(True)
    space._on_canvas_pressed(None, 1, 120.0, 80.0)

    assert len(space.text_boxes) == 2
    assert space.text_boxes[0] is not space.text_boxes[1]
    assert (space.text_boxes[0].x, space.text_boxes[0].y) == (120.0, 80.0)
    assert (space.text_boxes[1].x, space.text_boxes[1].y) == (120.0, 80.0)
    assert "editing" not in space.text_boxes[0].get_css_classes()
    assert "editing" in space.text_boxes[1].get_css_classes()

    space._on_canvas_pressed(None, 1, 150.0, 80.0)
    assert "editing" not in space.text_boxes[1].get_css_classes()

    space.text_boxes[0]._on_focus_enter(None)
    assert "editing" in space.text_boxes[0].get_css_classes()
    assert "editing" not in space.text_boxes[1].get_css_classes()
    space.text_boxes[1]._on_focus_enter(None)
    assert "editing" not in space.text_boxes[0].get_css_classes()
    assert "editing" in space.text_boxes[1].get_css_classes()
    space.text_boxes[1]._on_focus_leave(None)
    assert "editing" not in space.text_boxes[1].get_css_classes()


def test_textbox_can_move_and_box_size_scales_its_text() -> None:
    text_box = TextBox(
        Gtk.Fixed(),
        DrawingColor(),
        SpaceZoom(lambda: None),
        (20.0, 30.0),
        lambda _text_box: None,
        lambda _text_box: None,
        lambda _text_box: None,
    )
    initial_font_scale = text_box.font_scale

    text_box._on_move_begin(None, 0.0, 0.0)
    text_box._on_move_update(None, 40.0, 25.0)
    text_box._on_move_end(None, 40.0, 25.0)
    assert (text_box.x, text_box.y) == (60.0, 55.0)

    text_box._on_resize_begin(None, 0.0, 0.0, "se")
    text_box._on_resize_update(None, 70.0, 35.0, "se")
    assert text_box.font_scale > initial_font_scale


def test_textbox_drag_keeps_fractional_position_at_zoom() -> None:
    zoom = SpaceZoom(lambda: None)
    zoom.scale = 1.25
    board = Gtk.Fixed()
    text_box = TextBox(
        board,
        DrawingColor(),
        zoom,
        (20.0, 30.0),
        lambda _text_box: None,
        lambda _text_box: None,
        lambda _text_box: None,
    )

    text_box._on_move_begin(None, 0.0, 0.0)
    text_box._on_move_update(None, 2.5, 1.5)

    transform = board.get_child_transform(text_box)
    assert transform is not None
    _, _, _, _, x, y = transform.to_2d()
    assert (x, y) == (27.5, 39.0)


def test_space_color_selection_recolors_text_and_applies_to_new_input() -> None:
    panel = AnalysisPanel()
    space = panel._section_placeholders["Space"]
    space.tool_buttons["Text Box"].set_active(True)
    space._on_canvas_pressed(None, 1, 120.0, 80.0)
    text_box = space.text_boxes[0]
    text_box.buffer.insert(text_box.buffer.get_start_iter(), "A")
    text_box.buffer.select_range(
        text_box.buffer.get_start_iter(),
        text_box.buffer.get_iter_at_offset(1),
    )

    color = (0.9, 0.1, 0.1)
    space.drawing_color.set(color)
    assert "space-text-E61A1A" in _tag_names_at(text_box, 0)

    text_box.buffer.insert(text_box.buffer.get_end_iter(), "B")
    assert "space-text-E61A1A" in _tag_names_at(text_box, 1)
