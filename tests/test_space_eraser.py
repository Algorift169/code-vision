import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from codevision.space.eraser import Eraser
from codevision.space.pen import Pen


def test_eraser_removes_only_the_touched_part_and_supports_undo_redo() -> None:
    canvas = Gtk.DrawingArea()
    canvas.set_content_width(100)
    canvas.set_content_height(100)
    pen = Pen(canvas)
    pen.set_enabled(True)
    pen._on_drag_begin(None, 10.0, 50.0)
    pen._on_drag_end(None, 80.0, 0.0)

    eraser = Eraser(pen)
    eraser.set_enabled(True)
    eraser._on_pressed(None, 1, 50.0, 50.0)
    eraser._on_released(None, 1, 50.0, 50.0)

    assert pen.strokes == [
        [(10.0, 50.0), (42.5, 50.0)],
        [(57.5, 50.0), (90.0, 50.0)],
    ]
    eraser._on_motion(None, 20.0, 20.0)
    assert pen.eraser_cursor == ((20.0, 20.0), eraser.size)
    eraser._on_pointer_leave(None)
    assert eraser.enabled
    assert pen.eraser_cursor is None

    pen.undo()
    assert pen.strokes == [[(10.0, 50.0), (90.0, 50.0)]]

    pen.redo()
    assert len(pen.strokes) == 2
