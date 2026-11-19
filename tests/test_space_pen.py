import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from codevision.space.pen import Pen


def test_pen_draws_white_strokes_and_stops_when_pointer_leaves() -> None:
    canvas = Gtk.DrawingArea()
    canvas.set_content_width(100)
    canvas.set_content_height(100)
    pen = Pen(canvas)

    assert not pen.enabled
    assert pen.color == (1.0, 1.0, 1.0)
    assert not pen.can_undo
    assert not pen.can_redo

    pen._on_drag_begin(None, 10.0, 12.0)
    assert pen.strokes == []

    pen.set_enabled(True)
    pen._on_drag_begin(None, 10.0, 12.0)
    pen._on_drag_update(None, 5.0, 7.0)
    assert pen.strokes == [[(10.0, 12.0), (15.0, 19.0)]]
    assert not pen.can_undo
    assert not pen.can_redo

    pen._on_drag_end(None, 5.0, 7.0)
    assert pen.can_undo
    pen._on_pointer_leave(None)
    pen._on_drag_update(None, 9.0, 11.0)
    assert pen.strokes == [[(10.0, 12.0), (15.0, 19.0)]]

    pen.set_enabled(False)
    pen._on_drag_begin(None, 30.0, 30.0)
    assert pen.strokes == [[(10.0, 12.0), (15.0, 19.0)]]


def test_undo_and_redo_restore_strokes_and_new_strokes_clear_redo() -> None:
    from codevision.space.rendo import Redo
    from codevision.space.undo import Undo

    canvas = Gtk.DrawingArea()
    canvas.set_content_width(100)
    canvas.set_content_height(100)
    pen = Pen(canvas)
    pen.set_enabled(True)
    pen._on_drag_begin(None, 10.0, 12.0)
    pen._on_drag_end(None, 5.0, 7.0)
    assert pen.can_undo

    Undo(pen).execute()
    assert not pen.can_undo
    assert pen.can_redo
    assert pen.strokes == []

    Redo(pen).execute()
    assert pen.can_undo
    assert not pen.can_redo
    assert pen.strokes == [[(10.0, 12.0), (15.0, 19.0)]]

    Undo(pen).execute()
    pen._on_drag_begin(None, 30.0, 30.0)
    pen._on_drag_end(None, 0.0, 0.0)
    assert not pen.can_redo
