from __future__ import annotations

from collections.abc import Callable
import math

import cairo
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from codevision.shape.base import DiagramShape

from .color import Color
from .zoom import SpaceZoom


class ShapeItem(Gtk.Overlay):
    """A movable, resizable, zoom-aware shape on the Space board."""

    WIDTH = 144.0
    HEIGHT = 96.0
    MIN_WIDTH = 48.0
    MIN_HEIGHT = 32.0
    HANDLE_SIZE = 10
    ROTATION_HANDLE_SIZE = 14
    _DIRECTION_ANGLES = {
        "right": 0.0,
        "down": math.pi / 2,
        "left": math.pi,
        "up": -math.pi / 2,
    }
    _CORNERS = {
        "nw": (Gtk.Align.START, Gtk.Align.START, "nwse-resize"),
        "ne": (Gtk.Align.END, Gtk.Align.START, "nesw-resize"),
        "sw": (Gtk.Align.START, Gtk.Align.END, "nesw-resize"),
        "se": (Gtk.Align.END, Gtk.Align.END, "nwse-resize"),
    }

    def __init__(
        self,
        shape: DiagramShape,
        color: Color,
        zoom: SpaceZoom,
        position: tuple[float, float],
        on_geometry_changed: Callable[[ShapeItem], None],
        width: float = WIDTH,
        height: float = HEIGHT,
        direction: str = "right",
        rotation: float | None = None,
    ) -> None:
        super().__init__()
        self.shape = shape
        self.color = color
        self.zoom = zoom
        self.on_geometry_changed = on_geometry_changed
        self.x, self.y = position
        self.width = max(self.MIN_WIDTH, width)
        self.height = max(self.MIN_HEIGHT, height)
        if direction not in ("up", "right", "down", "left"):
            raise ValueError(f"Unsupported shape direction: {direction}")
        if rotation is not None and not math.isfinite(rotation):
            raise ValueError("Shape rotation must be a finite angle.")
        self.rotation = (
            self._DIRECTION_ANGLES[direction]
            if rotation is None
            else rotation % math.tau
        )
        self.direction = self._direction_for_rotation(self.rotation)
        self._resize_corner: str | None = None
        self._resize_origin = (self.x, self.y, self.width, self.height)
        self._rotating = False
        self._rotation_origin = self.rotation
        self._rotation_start_y = 0.0

        self.set_name("space-shape-item")
        self.add_css_class("space-shape-item")
        self.set_cursor_from_name("grab")

        self.canvas = Gtk.DrawingArea()
        self.canvas.set_hexpand(True)
        self.canvas.set_vexpand(True)
        self.canvas.set_can_target(False)
        self.canvas.set_draw_func(self._draw_shape)
        self.set_child(self.canvas)

        self.handles: dict[str, Gtk.DrawingArea] = {}
        for corner, (horizontal, vertical, cursor) in self._CORNERS.items():
            handle = Gtk.DrawingArea()
            handle.set_size_request(self.HANDLE_SIZE, self.HANDLE_SIZE)
            handle.set_halign(horizontal)
            handle.set_valign(vertical)
            handle.set_cursor_from_name(cursor)
            handle.add_css_class("space-shape-resize-handle")
            handle.set_tooltip_text("Drag to resize shape")
            handle.set_visible(False)
            drag = Gtk.GestureDrag.new()
            drag.connect("drag-begin", self._on_resize_begin, corner)
            drag.connect("drag-update", self._on_resize_update, corner)
            drag.connect("drag-end", self._on_resize_end, corner)
            handle.add_controller(drag)
            self.add_overlay(handle)
            self.handles[corner] = handle

        self.direction_control: Gtk.MenuButton | None = None
        self.direction_buttons: dict[str, Gtk.Button] = {}
        self.rotation_handle: Gtk.DrawingArea | None = None
        if self.shape.shape_id == "arrow":
            self._add_direction_control()
            self._add_rotation_handle()

        motion = Gtk.EventControllerMotion.new()
        motion.connect("enter", self._on_pointer_enter)
        motion.connect("leave", self._on_pointer_leave)
        self.add_controller(motion)
        self.apply_zoom()

    def _add_direction_control(self) -> None:
        control = Gtk.MenuButton()
        control.set_child(Gtk.Label(label="Direction"))
        control.set_tooltip_text("Adjust arrow direction")
        control.set_halign(Gtk.Align.CENTER)
        control.set_valign(Gtk.Align.END)
        control.set_margin_bottom(2)
        control.add_css_class("space-arrow-direction-control")
        control.set_visible(False)

        popover = Gtk.Popover()
        popover.set_position(Gtk.PositionType.BOTTOM)
        popover.set_autohide(True)
        choices = Gtk.Grid()
        choices.set_row_spacing(4)
        choices.set_column_spacing(4)
        for index, direction in enumerate(("up", "right", "down", "left")):
            button = Gtk.Button(label=direction.title())
            button.add_css_class("space-arrow-direction-option")
            button.connect("clicked", self._on_direction_selected, direction)
            choices.attach(button, index % 2, index // 2, 1, 1)
            self.direction_buttons[direction] = button
        popover.set_child(choices)
        control.set_popover(popover)
        popover.add_css_class("space-arrow-direction-popover")
        self.add_overlay(control)
        self.direction_control = control
        self._update_direction_buttons()

    def _add_rotation_handle(self) -> None:
        handle = Gtk.DrawingArea()
        handle.set_content_width(self.ROTATION_HANDLE_SIZE)
        handle.set_content_height(self.ROTATION_HANDLE_SIZE)
        handle.set_size_request(
            self.ROTATION_HANDLE_SIZE,
            self.ROTATION_HANDLE_SIZE,
        )
        handle.set_halign(Gtk.Align.CENTER)
        handle.set_valign(Gtk.Align.START)
        handle.set_margin_top(2)
        handle.set_cursor_from_name("crosshair")
        handle.set_tooltip_text("Drag to rotate arrow freely")
        handle.add_css_class("space-arrow-rotation-handle")
        handle.set_draw_func(self._draw_rotation_handle)
        handle.set_visible(False)
        drag = Gtk.GestureDrag.new()
        drag.connect("drag-begin", self._on_rotation_begin)
        drag.connect("drag-update", self._on_rotation_update)
        drag.connect("drag-end", self._on_rotation_end)
        handle.add_controller(drag)
        self.add_overlay(handle)
        self.rotation_handle = handle

    @staticmethod
    def _direction_for_rotation(rotation: float) -> str | None:
        normalized = rotation % math.tau
        nearest = min(
            ShapeItem._DIRECTION_ANGLES,
            key=lambda direction: abs(
                (normalized - ShapeItem._DIRECTION_ANGLES[direction] + math.pi)
                % math.tau
                - math.pi
            ),
        )
        difference = abs(
            (normalized - ShapeItem._DIRECTION_ANGLES[nearest] + math.pi)
            % math.tau
            - math.pi
        )
        return nearest if difference < math.radians(1) else None

    def apply_zoom(self) -> None:
        scaled_width = self.zoom.to_pixels(round(self.width))
        scaled_height = self.zoom.to_pixels(round(self.height))
        self.canvas.set_content_width(scaled_width)
        self.canvas.set_content_height(scaled_height)
        self.set_size_request(scaled_width, scaled_height)
        self.queue_draw()

    def _on_pointer_enter(
        self,
        _controller: Gtk.EventControllerMotion,
        _x: float,
        _y: float,
    ) -> None:
        self._set_handles_visible(True)

    def _on_pointer_leave(
        self,
        _controller: Gtk.EventControllerMotion,
    ) -> None:
        if self._resize_corner is not None or self._rotating:
            return
        if self.direction_control is not None and self.direction_control.get_active():
            return
        self._set_handles_visible(False)

    def _set_handles_visible(self, visible: bool) -> None:
        for handle in self.handles.values():
            handle.set_visible(visible)
        if self.direction_control is not None:
            self.direction_control.set_visible(visible)
        if self.rotation_handle is not None:
            self.rotation_handle.set_visible(visible)

    def _on_direction_selected(
        self,
        _button: Gtk.Button,
        direction: str,
    ) -> None:
        self.set_direction(direction)
        if self.direction_control is not None:
            popover = self.direction_control.get_popover()
            if isinstance(popover, Gtk.Popover):
                popover.popdown()

    def set_direction(self, direction: str) -> None:
        if self.shape.shape_id != "arrow":
            raise ValueError("Only arrow shapes have an adjustable direction.")
        if direction not in ("up", "right", "down", "left"):
            raise ValueError(f"Unsupported arrow direction: {direction}")
        self.set_rotation(self._DIRECTION_ANGLES[direction])

    def set_rotation(self, rotation: float) -> None:
        if self.shape.shape_id != "arrow":
            raise ValueError("Only arrow shapes can be rotated.")
        if not math.isfinite(rotation):
            raise ValueError("Arrow rotation must be a finite angle.")
        self.rotation = rotation % math.tau
        self.direction = self._direction_for_rotation(self.rotation)
        self._update_direction_buttons()
        self.queue_draw()

    def _update_direction_buttons(self) -> None:
        for direction, button in self.direction_buttons.items():
            if direction == self.direction:
                button.add_css_class("suggested-action")
            else:
                button.remove_css_class("suggested-action")

    def _on_rotation_begin(
        self,
        _gesture: Gtk.GestureDrag,
        _x: float,
        _y: float,
    ) -> None:
        self._rotating = True
        self._rotation_origin = self.rotation
        handle_center_y = 2 + self.ROTATION_HANDLE_SIZE / 2
        self._rotation_start_y = (
            handle_center_y - self.height * self.zoom.scale / 2
        )
        self._set_handles_visible(True)

    def _on_rotation_update(
        self,
        _gesture: Gtk.GestureDrag,
        offset_x: float,
        offset_y: float,
    ) -> None:
        if not self._rotating:
            return
        initial_angle = math.atan2(self._rotation_start_y, 0)
        pointer_angle = math.atan2(
            self._rotation_start_y + offset_y,
            offset_x,
        )
        self.set_rotation(
            self._rotation_origin + pointer_angle - initial_angle
        )

    def _on_rotation_end(
        self,
        _gesture: Gtk.GestureDrag,
        _offset_x: float,
        _offset_y: float,
    ) -> None:
        self._rotating = False
        self._set_handles_visible(False)

    def _draw_rotation_handle(
        self,
        _area: Gtk.DrawingArea,
        context: cairo.Context,
        width: int,
        height: int,
    ) -> None:
        context.arc(
            width / 2,
            height / 2,
            min(width, height) * 0.35,
            0,
            math.tau,
        )
        context.set_source_rgb(*self.color)
        context.fill_preserve()
        context.set_source_rgb(0.16, 0.16, 0.16)
        context.set_line_width(1.0)
        context.stroke()

    def _on_resize_begin(
        self,
        _gesture: Gtk.GestureDrag,
        _x: float,
        _y: float,
        corner: str,
    ) -> None:
        self._resize_corner = corner
        self._resize_origin = (self.x, self.y, self.width, self.height)
        self._set_handles_visible(True)

    def _on_resize_update(
        self,
        _gesture: Gtk.GestureDrag,
        offset_x: float,
        offset_y: float,
        corner: str,
    ) -> None:
        if corner != self._resize_corner:
            return
        x, y, width, height = self._resize_origin
        dx = offset_x / self.zoom.scale
        dy = offset_y / self.zoom.scale
        left = corner in ("nw", "sw")
        top = corner in ("nw", "ne")

        new_width = max(self.MIN_WIDTH, width - dx if left else width + dx)
        new_height = max(self.MIN_HEIGHT, height - dy if top else height + dy)
        self.x = max(0.0, x + width - new_width) if left else x
        self.y = max(0.0, y + height - new_height) if top else y
        if left:
            new_width = x + width - self.x
        if top:
            new_height = y + height - self.y

        self.width = new_width
        self.height = new_height
        self.apply_zoom()
        self.on_geometry_changed(self)

    def _on_resize_end(
        self,
        _gesture: Gtk.GestureDrag,
        _offset_x: float,
        _offset_y: float,
        corner: str,
    ) -> None:
        if corner == self._resize_corner:
            self._resize_corner = None
            self._set_handles_visible(False)

    def _draw_shape(
        self,
        _area: Gtk.DrawingArea,
        context: cairo.Context,
        width: int,
        height: int,
    ) -> None:
        if width <= 0 or height <= 0:
            return
        context.save()
        context.scale(width / self.width, height / self.height)
        self.shape.draw(
            context,
            self.width,
            self.height,
            self.color,
            self.rotation,
        )
        context.restore()
