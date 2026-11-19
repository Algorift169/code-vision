from __future__ import annotations

import math
from dataclasses import replace

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from .graph_data import GraphNodeData, GraphTextLine
from .zoom import SpaceZoom


class GraphNodeItem(Gtk.DrawingArea):
    """A draggable graph node that retains the source renderer's appearance."""

    def __init__(
        self,
        node: GraphNodeData,
        zoom: SpaceZoom,
        position: tuple[float, float],
        scale: float = 1.0,
    ) -> None:
        super().__init__()
        self.node = node
        self.zoom = zoom
        self.x, self.y = position
        self.scale = scale
        self.width = node.width * scale
        self.height = node.height * scale
        self.title = node.title
        self.set_name("space-graph-node")
        self.add_css_class("space-graph-node")
        self.set_cursor_from_name("grab")
        self.set_draw_func(self._draw)
        self.apply_zoom()

    def set_title(self, title: str) -> None:
        self.title = title.strip()
        if self.node.text_lines:
            self.node = replace(
                self.node,
                text_lines=(
                    replace(self.node.text_lines[0], text=self.title),
                    *self.node.text_lines[1:],
                ),
            )
        self.queue_draw()

    def apply_zoom(self) -> None:
        self.set_content_width(math.ceil(self.zoom.to_pixels(self.width)))
        self.set_content_height(math.ceil(self.zoom.to_pixels(self.height)))
        self.set_size_request(
            math.ceil(self.zoom.to_pixels(self.width)),
            math.ceil(self.zoom.to_pixels(self.height)),
        )

    def _draw(self, _area: Gtk.DrawingArea, context, width: int, height: int) -> None:
        if width <= 0 or height <= 0:
            return
        node = self.node
        scale_x = width / node.width
        scale_y = height / node.height
        context.save()
        context.scale(scale_x, scale_y)
        context.set_line_width(node.stroke_width)
        self._append_shape(context, node)
        context.set_source_rgba(*node.fill_color)
        context.fill_preserve()
        context.set_source_rgba(*node.stroke_color)
        context.stroke()
        context.select_font_face("Sans", 0, 0)
        context.set_source_rgba(*node.text_color)
        lines = node.text_lines or (
            GraphTextLine(self.title, 12, node.height * 0.42),
            GraphTextLine(node.detail, 12, node.height * 0.72, 10),
        )
        for line in lines:
            context.set_font_size(line.font_size)
            text_x = line.x
            if line.alignment == "center":
                extents = context.text_extents(line.text)
                text_x -= extents.width / 2 + extents.x_bearing
            context.move_to(text_x, line.y)
            context.show_text(line.text)
        context.restore()

    @staticmethod
    def _append_shape(context, node: GraphNodeData) -> None:
        width, height = node.width, node.height
        shape = node.shape
        if shape == "circle":
            context.arc(width / 2, height / 2, height / 2, 0, math.tau)
            context.close_path()
        elif shape == "small-circle":
            context.arc(width / 2, height / 2, min(width, height) / 5, 0, math.tau)
            context.close_path()
        elif shape == "diamond":
            context.move_to(width / 2, 0)
            context.line_to(width, height / 2)
            context.line_to(width / 2, height)
            context.line_to(0, height / 2)
            context.close_path()
        elif shape == "parallelogram":
            context.move_to(16, 0)
            context.line_to(width, 0)
            context.line_to(width - 16, height)
            context.line_to(0, height)
            context.close_path()
        elif shape == "hexagon":
            context.move_to(18, 0)
            context.line_to(width - 18, 0)
            context.line_to(width, height / 2)
            context.line_to(width - 18, height)
            context.line_to(18, height)
            context.line_to(0, height / 2)
            context.close_path()
        else:
            context.rectangle(0, 0, width, height)
