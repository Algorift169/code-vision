from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import math

import cairo
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from .color import Color, DrawingColor


Point = tuple[float, float]
Stroke = list[Point]
BoardSnapshot = tuple[list[Stroke], list[Color]]


@dataclass
class _DrawAction:
    index: int
    stroke: Stroke
    color: Color


@dataclass
class _EraseAction:
    before: BoardSnapshot
    after: BoardSnapshot


class Pen:
    """Draw freehand strokes using the shared Space color."""

    line_width = 3.0

    def __init__(
        self,
        canvas: Gtk.DrawingArea,
        on_history_changed: Callable[[], None] | None = None,
        drawing_color: DrawingColor | None = None,
    ) -> None:
        self.canvas = canvas
        self.drawing_color = drawing_color or DrawingColor()
        self.strokes: list[Stroke] = []
        self.stroke_colors: list[Color] = []
        self._undo_stack: list[_DrawAction | _EraseAction] = []
        self._redo_stack: list[_DrawAction | _EraseAction] = []
        self._active_stroke: Stroke | None = None
        self._active_stroke_index: int | None = None
        self._active_color: Color | None = None
        self._drag_origin = (0.0, 0.0)
        self.enabled = False
        self._on_history_changed = on_history_changed
        self.eraser_cursor: tuple[Point, float] | None = None

        canvas.set_draw_func(self._draw)

        drag = Gtk.GestureDrag.new()
        drag.connect("drag-begin", self._on_drag_begin)
        drag.connect("drag-update", self._on_drag_update)
        drag.connect("drag-end", self._on_drag_end)
        canvas.add_controller(drag)

        motion = Gtk.EventControllerMotion.new()
        motion.connect("leave", self._on_pointer_leave)
        canvas.add_controller(motion)

    @property
    def can_undo(self) -> bool:
        return bool(self._undo_stack)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo_stack)

    @property
    def color(self) -> Color:
        return self.drawing_color.current

    def set_enabled(self, enabled: bool) -> None:
        if self.enabled and not enabled:
            self._finish_active_stroke()
        self.enabled = enabled

    def _on_drag_begin(
        self, _gesture: Gtk.GestureDrag, x: float, y: float
    ) -> None:
        if not self.enabled:
            return
        self._drag_origin = (x, y)
        self._active_stroke = [(x, y)]
        self._active_stroke_index = len(self.strokes)
        self._active_color = self.color
        self.strokes.append(self._active_stroke)
        self.stroke_colors.append(self._active_color)
        self.canvas.queue_draw()

    def _on_drag_update(
        self, _gesture: Gtk.GestureDrag, offset_x: float, offset_y: float
    ) -> None:
        if not self.enabled or self._active_stroke is None:
            return
        x = self._drag_origin[0] + offset_x
        y = self._drag_origin[1] + offset_y
        width = max(self.canvas.get_width(), self.canvas.get_content_width())
        height = max(self.canvas.get_height(), self.canvas.get_content_height())
        if not (0 <= x <= width and 0 <= y <= height):
            self._active_stroke = None
            return
        if self._active_stroke[-1] != (x, y):
            self._active_stroke.append((x, y))
            self.canvas.queue_draw()

    def _on_drag_end(
        self, _gesture: Gtk.GestureDrag, offset_x: float, offset_y: float
    ) -> None:
        self._on_drag_update(_gesture, offset_x, offset_y)
        self._finish_active_stroke()

    def _on_pointer_leave(
        self, _controller: Gtk.EventControllerMotion
    ) -> None:
        self._finish_active_stroke()

    def undo(self) -> None:
        self._finish_active_stroke()
        if not self._undo_stack:
            return
        action = self._undo_stack.pop()
        if isinstance(action, _DrawAction):
            if action.index < len(self.strokes):
                del self.strokes[action.index]
                del self.stroke_colors[action.index]
        else:
            self._restore_snapshot(action.before)
        self._redo_stack.append(action)
        self.canvas.queue_draw()
        self._notify_history_changed()

    def redo(self) -> None:
        self._finish_active_stroke()
        if not self._redo_stack:
            return
        action = self._redo_stack.pop()
        if isinstance(action, _DrawAction):
            index = min(action.index, len(self.strokes))
            self.strokes.insert(index, action.stroke.copy())
            self.stroke_colors.insert(index, action.color)
        else:
            self._restore_snapshot(action.after)
        self._undo_stack.append(action)
        self.canvas.queue_draw()
        self._notify_history_changed()

    def snapshot(self) -> BoardSnapshot:
        return self._copy_snapshot(self.strokes, self.stroke_colors)

    def record_erasure(self, before: BoardSnapshot) -> None:
        after = self.snapshot()
        if before == after:
            return
        self._record_action(_EraseAction(before, after))

    def set_eraser_cursor(
        self, position: Point | None, size: float = 0.0
    ) -> None:
        self.eraser_cursor = (position, size) if position is not None else None
        self.canvas.queue_draw()

    def _finish_active_stroke(self) -> None:
        if self._active_stroke is None or self._active_stroke_index is None:
            return
        self._record_action(
            _DrawAction(
                self._active_stroke_index,
                self._active_stroke.copy(),
                self._active_color or self.color,
            )
        )
        self._active_stroke = None
        self._active_stroke_index = None
        self._active_color = None

    def _record_action(self, action: _DrawAction | _EraseAction) -> None:
        self._undo_stack.append(action)
        self._redo_stack.clear()
        self._notify_history_changed()

    @staticmethod
    def _copy_strokes(strokes: list[Stroke]) -> list[Stroke]:
        return [stroke.copy() for stroke in strokes]

    @classmethod
    def _copy_snapshot(
        cls, strokes: list[Stroke], colors: list[Color]
    ) -> BoardSnapshot:
        return cls._copy_strokes(strokes), colors.copy()

    def _restore_snapshot(self, snapshot: BoardSnapshot) -> None:
        strokes, colors = snapshot
        self.strokes[:] = self._copy_strokes(strokes)
        self.stroke_colors[:] = colors

    def _notify_history_changed(self) -> None:
        if self._on_history_changed is not None:
            self._on_history_changed()

    def _draw(
        self, _canvas: Gtk.DrawingArea, context, _width: int, _height: int
    ) -> None:
        context.set_source_rgb(*self.color)
        context.set_line_width(self.line_width)
        context.set_line_cap(cairo.LINE_CAP_ROUND)
        context.set_line_join(cairo.LINE_JOIN_ROUND)

        for stroke, color in zip(self.strokes, self.stroke_colors):
            context.set_source_rgb(*color)
            if len(stroke) == 1:
                x, y = stroke[0]
                context.arc(x, y, self.line_width / 2, 0, 2 * math.pi)
                context.fill()
                continue
            context.move_to(*stroke[0])
            for point in stroke[1:]:
                context.line_to(*point)
            context.stroke()

        if self.eraser_cursor is not None:
            (x, y), size = self.eraser_cursor
            context.rectangle(x - size / 2, y - size / 2, size, size)
            context.set_source_rgb(1.0, 1.0, 1.0)
            context.fill_preserve()
            context.set_source_rgb(0.25, 0.25, 0.25)
            context.set_line_width(1.0)
            context.stroke()
