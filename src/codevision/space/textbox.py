from __future__ import annotations

from collections.abc import Callable
import math

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from .color import Color, DrawingColor
from .zoom import SpaceZoom


class TextBox(Gtk.Overlay):
    """Editable, independently positioned rich-text box on the Space board."""

    MIN_WIDTH = 72.0
    MIN_HEIGHT = 36.0
    DEFAULT_WIDTH = 140.0
    DEFAULT_HEIGHT = 70.0
    BASE_FONT_SIZE = 14.0
    HANDLE_SIZE = 10
    MOVE_HANDLE_WIDTH = 36
    MOVE_HANDLE_HEIGHT = 8
    _CORNERS = {
        "nw": (Gtk.Align.START, Gtk.Align.START, "nwse-resize"),
        "ne": (Gtk.Align.END, Gtk.Align.START, "nesw-resize"),
        "sw": (Gtk.Align.START, Gtk.Align.END, "nesw-resize"),
        "se": (Gtk.Align.END, Gtk.Align.END, "nwse-resize"),
    }

    def __init__(
        self,
        board: Gtk.Fixed,
        drawing_color: DrawingColor,
        zoom: SpaceZoom,
        position: tuple[float, float],
        on_focus: Callable[[TextBox], None],
        on_blur: Callable[[TextBox], None],
        on_geometry_changed: Callable[[TextBox], None],
    ) -> None:
        super().__init__()
        self.board = board
        self.drawing_color = drawing_color
        self.zoom = zoom
        self.on_focus = on_focus
        self.on_blur = on_blur
        self.on_geometry_changed = on_geometry_changed
        self.x, self.y = position
        self.width = self.DEFAULT_WIDTH
        self.height = self.DEFAULT_HEIGHT
        self.title = ""
        self._tags: dict[Color, Gtk.TextTag] = {}
        self._inserting_colored_text = False
        self._highlighted = False
        self._resizing = False
        self._moving = False
        self._resize_corner: str | None = None
        self._resize_origin = (0.0, 0.0, self.width, self.height)
        self._move_origin = (self.x, self.y)

        self.set_name("space-text-box")
        self.add_css_class("space-text-box")

        self.text_view = Gtk.TextView()
        self.text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.text_view.set_left_margin(4)
        self.text_view.set_right_margin(4)
        self.text_view.set_top_margin(13)
        self.text_view.set_bottom_margin(3)
        self.text_view.add_css_class("space-text-view")
        self.buffer = self.text_view.get_buffer()
        self.buffer.connect("insert-text", self._on_insert_text)

        self.scroller = Gtk.ScrolledWindow()
        self.scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.NEVER)
        self.scroller.set_hexpand(True)
        self.scroller.set_vexpand(True)
        self.scroller.set_child(self.text_view)
        self.set_child(self.scroller)

        self.title_label = Gtk.Label()
        self.title_label.set_halign(Gtk.Align.START)
        self.title_label.set_valign(Gtk.Align.START)
        self.title_label.set_margin_start(5)
        self.title_label.set_margin_top(1)
        self.title_label.add_css_class("space-text-box-title")
        self.title_label.set_can_target(False)
        self.title_label.set_visible(False)
        self.add_overlay(self.title_label)

        self.handles: dict[str, Gtk.DrawingArea] = {}
        for corner, (horizontal, vertical, cursor) in self._CORNERS.items():
            handle = Gtk.DrawingArea()
            handle.set_size_request(self.HANDLE_SIZE, self.HANDLE_SIZE)
            handle.set_halign(horizontal)
            handle.set_valign(vertical)
            handle.set_cursor_from_name(cursor)
            handle.add_css_class("space-text-box-handle")
            handle.set_visible(False)
            drag = Gtk.GestureDrag.new()
            drag.connect("drag-begin", self._on_resize_begin, corner)
            drag.connect("drag-update", self._on_resize_update, corner)
            drag.connect("drag-end", self._on_resize_end, corner)
            handle.add_controller(drag)
            self.add_overlay(handle)
            self.handles[corner] = handle

        self.move_handle = Gtk.DrawingArea()
        self.move_handle.set_size_request(
            self.MOVE_HANDLE_WIDTH, self.MOVE_HANDLE_HEIGHT
        )
        self.move_handle.set_halign(Gtk.Align.CENTER)
        self.move_handle.set_valign(Gtk.Align.START)
        self.move_handle.set_cursor_from_name("grab")
        self.move_handle.set_tooltip_text("Drag to move text box")
        self.move_handle.add_css_class("space-text-box-move-handle")
        self.move_handle.set_visible(False)
        move_gesture = Gtk.GestureDrag.new()
        move_gesture.connect("drag-begin", self._on_move_begin)
        move_gesture.connect("drag-update", self._on_move_update)
        move_gesture.connect("drag-end", self._on_move_end)
        self.board.add_controller(move_gesture)
        self.add_overlay(self.move_handle)

        focus = Gtk.EventControllerFocus.new()
        focus.connect("enter", self._on_focus_enter)
        focus.connect("leave", self._on_focus_leave)
        self.text_view.add_controller(focus)

        self.board.put(self, self.zoom.to_pixels(self.x), self.zoom.to_pixels(self.y))
        self.set_highlighted(True)
        self._apply_zoom()
        self.on_focus(self)
        self.text_view.grab_focus()

    def apply_zoom(self) -> None:
        self._apply_zoom()

    @property
    def font_scale(self) -> float:
        area_ratio = (self.width * self.height) / (
            self.DEFAULT_WIDTH * self.DEFAULT_HEIGHT
        )
        return max(0.6, min(3.0, math.sqrt(area_ratio)))

    def apply_color_to_selection(self, color: Color) -> None:
        selection = self.buffer.get_selection_bounds()
        if not selection:
            return
        start, end = selection
        tag = self._tag_for_color(color)
        for existing_tag in self._tags.values():
            self.buffer.remove_tag(existing_tag, start, end)
        self.buffer.apply_tag(tag, start, end)

    def set_title(self, title: str) -> None:
        self.title = title.strip()
        self.title_label.set_text(self.title)
        self.title_label.set_visible(bool(self.title))
        self.text_view.set_top_margin(30 if self.title else 13)

    def copy_content_from(self, source: TextBox) -> None:
        self.width = source.width
        self.height = source.height
        self.set_title(source.title)
        source_buffer = source.buffer
        text = source_buffer.get_text(
            source_buffer.get_start_iter(), source_buffer.get_end_iter(), True
        )
        self.buffer.set_text(text)
        start = self.buffer.get_start_iter()
        end = self.buffer.get_end_iter()
        for existing_tag in self._tags.values():
            self.buffer.remove_tag(existing_tag, start, end)

        char_count = source_buffer.get_char_count()
        for color, source_tag in source._tags.items():
            run_start: int | None = None
            for offset in range(char_count + 1):
                has_tag = (
                    offset < char_count
                    and source_tag
                    in source_buffer.get_iter_at_offset(offset).get_tags()
                )
                if has_tag and run_start is None:
                    run_start = offset
                elif not has_tag and run_start is not None:
                    self.buffer.apply_tag(
                        self._tag_for_color(color),
                        self.buffer.get_iter_at_offset(run_start),
                        self.buffer.get_iter_at_offset(offset),
                    )
                    run_start = None
        self._apply_zoom()

    def _apply_zoom(self) -> None:
        self.set_size_request(
            self.zoom.to_pixels(round(self.width)),
            self.zoom.to_pixels(round(self.height)),
        )
        self.board.move(
            self,
            self.x * self.zoom.scale,
            self.y * self.zoom.scale,
        )
        for tag in self._tags.values():
            tag.set_property("scale", self.zoom.scale * self.font_scale)

    def _on_insert_text(
        self,
        buffer: Gtk.TextBuffer,
        location: Gtk.TextIter,
        text: str,
        _length: int,
    ) -> None:
        if self._inserting_colored_text:
            return
        buffer.stop_emission_by_name("insert-text")
        start_mark = buffer.create_mark(None, location, True)
        end_mark = buffer.create_mark(None, location, False)
        tag = self._tag_for_color(self.drawing_color.current)
        self._inserting_colored_text = True
        try:
            buffer.insert(buffer.get_iter_at_mark(end_mark), text)
            start = buffer.get_iter_at_mark(start_mark)
            end = buffer.get_iter_at_mark(end_mark)
            buffer.apply_tag(tag, start, end)
        finally:
            self._inserting_colored_text = False
            buffer.delete_mark(start_mark)
            buffer.delete_mark(end_mark)

    def _tag_for_color(self, color: Color) -> Gtk.TextTag:
        tag = self._tags.get(color)
        if tag is not None:
            return tag
        hex_color = "#" + "".join(
            f"{round(component * 255):02X}" for component in color
        )
        tag = self.buffer.create_tag(
            f"space-text-{hex_color[1:]}",
            foreground=hex_color,
            scale=self.zoom.scale * self.font_scale,
        )
        self._tags[color] = tag
        return tag

    def _on_focus_enter(self, _controller: Gtk.EventControllerFocus) -> None:
        self.on_focus(self)

    def _on_focus_leave(self, _controller: Gtk.EventControllerFocus) -> None:
        self.on_blur(self)

    def set_highlighted(self, highlighted: bool) -> None:
        self._highlighted = highlighted
        if highlighted or self._resizing or self._moving:
            self.add_css_class("editing")
        else:
            self.remove_css_class("editing")
        visible = highlighted or self._resizing or self._moving
        for handle in self.handles.values():
            handle.set_visible(visible)
        self.move_handle.set_visible(visible)

    def _on_move_begin(
        self, gesture: Gtk.GestureDrag, x: float, y: float
    ) -> None:
        if gesture is not None:
            picked = self.board.pick(x, y, Gtk.PickFlags.DEFAULT)
            while picked is not None and picked is not self.move_handle:
                picked = picked.get_parent()
            if picked is not self.move_handle:
                gesture.set_state(Gtk.EventSequenceState.DENIED)
                return
            gesture.set_state(Gtk.EventSequenceState.CLAIMED)
        self._moving = True
        self._move_origin = (self.x, self.y)
        self.set_highlighted(True)
        self.on_focus(self)

    def _on_move_update(
        self,
        _gesture: Gtk.GestureDrag,
        offset_x: float,
        offset_y: float,
    ) -> None:
        if not self._moving:
            return
        self.x = max(0.0, self._move_origin[0] + offset_x / self.zoom.scale)
        self.y = max(0.0, self._move_origin[1] + offset_y / self.zoom.scale)
        self.board.move(
            self,
            self.x * self.zoom.scale,
            self.y * self.zoom.scale,
        )
        self.on_geometry_changed(self)

    def _on_move_end(
        self, _gesture: Gtk.GestureDrag, _offset_x: float, _offset_y: float
    ) -> None:
        self._moving = False
        self.set_highlighted(self.text_view.has_focus())

    def _on_resize_begin(
        self,
        _gesture: Gtk.GestureDrag,
        _x: float,
        _y: float,
        corner: str,
    ) -> None:
        self._resize_corner = corner
        self._resize_origin = (self.x, self.y, self.width, self.height)
        self._resizing = True
        self.set_highlighted(True)
        self.on_focus(self)

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
        self._apply_zoom()
        self.on_geometry_changed(self)

    def _on_resize_end(
        self,
        _gesture: Gtk.GestureDrag,
        _offset_x: float,
        _offset_y: float,
        corner: str,
    ) -> None:
        if corner != self._resize_corner:
            return
        self._resizing = False
        self._resize_corner = None
        self.set_highlighted(self.text_view.has_focus())
