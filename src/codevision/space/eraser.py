from __future__ import annotations

import math

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gtk

from .pen import BoardSnapshot, Pen, Point, Stroke
from .zoom import SpaceZoom


class Eraser:
    """Remove small portions of existing strokes as the pointer is dragged."""

    size = 12.0

    def __init__(self, pen: Pen, zoom: SpaceZoom | None = None) -> None:
        self.pen = pen
        self.canvas = pen.canvas
        self.zoom = zoom or pen.zoom
        self.enabled = False
        self._dragging = False
        self._drag_origin: Point = (0.0, 0.0)
        self._last_position: Point | None = None
        self._before: BoardSnapshot | None = None

        click = Gtk.GestureClick.new()
        click.set_button(Gdk.BUTTON_PRIMARY)
        click.connect("pressed", self._on_pressed)
        click.connect("released", self._on_released)
        self.canvas.add_controller(click)

        drag = Gtk.GestureDrag.new()
        drag.connect("drag-begin", self._on_drag_begin)
        drag.connect("drag-update", self._on_drag_update)
        drag.connect("drag-end", self._on_drag_end)
        self.canvas.add_controller(drag)

        motion = Gtk.EventControllerMotion.new()
        motion.connect("enter", self._on_motion)
        motion.connect("motion", self._on_motion)
        motion.connect("leave", self._on_pointer_leave)
        self.canvas.add_controller(motion)

    def set_enabled(self, enabled: bool) -> None:
        if self.enabled and not enabled:
            self._finish_erasing()
        self.enabled = enabled
        if not enabled:
            self.pen.set_eraser_cursor(None)

    def _on_pressed(
        self, _gesture: Gtk.GestureClick, _count: int, x: float, y: float
    ) -> None:
        if not self.enabled:
            return
        self._begin_erasing(*self.zoom.to_board(x, y))

    def _on_released(
        self, _gesture: Gtk.GestureClick, _count: int, _x: float, _y: float
    ) -> None:
        self._finish_erasing()

    def _on_drag_begin(
        self, _gesture: Gtk.GestureDrag, x: float, y: float
    ) -> None:
        if not self.enabled:
            return
        self._drag_origin = (x, y)
        if not self._dragging:
            self._begin_erasing(*self.zoom.to_board(x, y))

    def _on_drag_update(
        self, _gesture: Gtk.GestureDrag, offset_x: float, offset_y: float
    ) -> None:
        if not self.enabled or not self._dragging:
            return
        x, y = self.zoom.to_board(
            self._drag_origin[0] + offset_x,
            self._drag_origin[1] + offset_y,
        )
        self._erase_sweep(x, y)
        self.pen.set_eraser_cursor((x, y), self.size)

    def _on_drag_end(
        self, _gesture: Gtk.GestureDrag, offset_x: float, offset_y: float
    ) -> None:
        self._on_drag_update(_gesture, offset_x, offset_y)
        self._finish_erasing()

    def _on_motion(
        self, _controller: Gtk.EventControllerMotion, x: float, y: float
    ) -> None:
        if self.enabled and not self._dragging:
            self.pen.set_eraser_cursor(self.zoom.to_board(x, y), self.size)

    def _on_pointer_leave(
        self, _controller: Gtk.EventControllerMotion
    ) -> None:
        self._finish_erasing()
        self.pen.set_eraser_cursor(None)

    def _begin_erasing(self, x: float, y: float) -> None:
        if self._dragging:
            return
        self._before = self.pen.snapshot()
        self._dragging = True
        self._last_position = (x, y)
        self._erase_at(x, y)
        self.pen.set_eraser_cursor((x, y), self.size)

    def _finish_erasing(self) -> None:
        if self._before is not None:
            self.pen.record_erasure(self._before)
        self._before = None
        self._last_position = None
        self._dragging = False

    def _erase_sweep(self, x: float, y: float) -> None:
        if self._last_position is None:
            self._erase_at(x, y)
        else:
            last_x, last_y = self._last_position
            distance = math.hypot(x - last_x, y - last_y)
            steps = max(1, math.ceil(distance / (self.size / 2)))
            for step in range(1, steps + 1):
                ratio = step / steps
                self._erase_at(
                    last_x + (x - last_x) * ratio,
                    last_y + (y - last_y) * ratio,
                )
        self._last_position = (x, y)

    def _erase_at(self, x: float, y: float) -> None:
        half_size = self.size / 2 + self.pen.line_width / 2
        bounds = (
            x - half_size,
            y - half_size,
            x + half_size,
            y + half_size,
        )
        remaining: list[Stroke] = []
        remaining_colors = []
        for stroke, color in zip(self.pen.strokes, self.pen.stroke_colors):
            erased_strokes = self._erase_stroke(stroke, bounds)
            remaining.extend(erased_strokes)
            remaining_colors.extend([color] * len(erased_strokes))
        if (
            remaining != self.pen.strokes
            or remaining_colors != self.pen.stroke_colors
        ):
            self.pen.strokes[:] = remaining
            self.pen.stroke_colors[:] = remaining_colors
            self.canvas.queue_draw()

    @classmethod
    def _erase_stroke(
        cls, stroke: Stroke, bounds: tuple[float, float, float, float]
    ) -> list[Stroke]:
        if len(stroke) == 1:
            x, y = stroke[0]
            x_min, y_min, x_max, y_max = bounds
            return [] if x_min <= x <= x_max and y_min <= y <= y_max else [stroke]

        paths: list[Stroke] = []
        current: Stroke = []
        for start, end in zip(stroke, stroke[1:]):
            interval = cls._clipped_interval(start, end, bounds)
            if interval is None:
                cls._append_point(current, start)
                cls._append_point(current, end)
                continue

            enter, leave = interval
            if enter > 0:
                cls._append_point(current, start)
                cls._append_point(current, cls._point_at(start, end, enter))
                if len(current) > 1:
                    paths.append(current)
            elif len(current) > 1:
                paths.append(current)

            current = []
            if leave < 1:
                current = [cls._point_at(start, end, leave), end]

        if len(current) > 1:
            paths.append(current)
        return paths

    @staticmethod
    def _append_point(path: Stroke, point: Point) -> None:
        if not path or path[-1] != point:
            path.append(point)

    @staticmethod
    def _point_at(start: Point, end: Point, ratio: float) -> Point:
        return (
            start[0] + (end[0] - start[0]) * ratio,
            start[1] + (end[1] - start[1]) * ratio,
        )

    @staticmethod
    def _clipped_interval(
        start: Point,
        end: Point,
        bounds: tuple[float, float, float, float],
    ) -> tuple[float, float] | None:
        x_min, y_min, x_max, y_max = bounds
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        lower, upper = 0.0, 1.0

        for direction, distance in (
            (-dx, start[0] - x_min),
            (dx, x_max - start[0]),
            (-dy, start[1] - y_min),
            (dy, y_max - start[1]),
        ):
            if direction == 0:
                if distance < 0:
                    return None
                continue
            ratio = distance / direction
            if direction < 0:
                lower = max(lower, ratio)
            else:
                upper = min(upper, ratio)
            if lower > upper:
                return None
        return lower, upper
