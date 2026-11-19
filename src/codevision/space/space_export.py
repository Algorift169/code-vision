from __future__ import annotations

import math
from pathlib import Path

import cairo
import gi

gi.require_version("Pango", "1.0")
gi.require_version("PangoCairo", "1.0")
from gi.repository import GdkPixbuf, GLib, Pango, PangoCairo

from .graph_item import GraphNodeItem
from .graph_data import GraphTextLine


class SpaceExporter:
    """Render every live Space board item to PNG or PDF at board coordinates."""

    def export_png(self, space, output_path: str | Path) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        width, height = self._board_size(space)
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        context = cairo.Context(surface)
        self._draw_board(context, space, width, height)
        surface.write_to_png(str(path))
        return path

    def export_pdf(self, space, output_path: str | Path) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        width, height = self._board_size(space)
        surface = cairo.PDFSurface(str(path), width, height)
        context = cairo.Context(surface)
        self._draw_board(context, space, width, height)
        surface.finish()
        return path

    @staticmethod
    def _board_size(space) -> tuple[int, int]:
        width = max(1, int(getattr(space, "_canvas_width", 0) or 0))
        height = max(1, int(getattr(space, "_canvas_height", 0) or 0))
        for item in (
            *getattr(space, "text_boxes", []),
            *getattr(space, "import_items", []),
            *getattr(space, "graph_items", []),
            *getattr(space, "shape_items", []),
        ):
            width = max(width, math.ceil(getattr(item, "x", 0) + getattr(item, "width", getattr(item, "WIDTH", 0))))
            height = max(height, math.ceil(getattr(item, "y", 0) + getattr(item, "height", getattr(item, "HEIGHT", 0))))
        return width, height

    def _draw_board(self, context: cairo.Context, space, width: int, height: int) -> None:
        context.save()
        context.set_source_rgb(0.055, 0.065, 0.085)
        context.rectangle(0, 0, width, height)
        context.fill()

        pen = getattr(space, "pen", None)
        if pen is not None:
            for stroke, color in zip(getattr(pen, "strokes", []), getattr(pen, "stroke_colors", [])):
                if not stroke:
                    continue
                context.save()
                context.set_source_rgb(*color)
                context.set_line_width(pen.line_width)
                context.set_line_cap(cairo.LINE_CAP_ROUND)
                context.set_line_join(cairo.LINE_JOIN_ROUND)
                if len(stroke) == 1:
                    x, y = stroke[0]
                    context.arc(x, y, pen.line_width / 2, 0, math.tau)
                    context.fill()
                else:
                    context.move_to(*stroke[0])
                    for point in stroke[1:]:
                        context.line_to(*point)
                    context.stroke()
                context.restore()

        for item in getattr(space, "text_boxes", []):
            self._draw_text_box(context, item)
        for item in getattr(space, "graph_items", []):
            self._draw_graph_item(context, item)
        for item in getattr(space, "shape_items", []):
            self._draw_shape_item(context, item)
        for item in getattr(space, "import_items", []):
            self._draw_import_item(context, item)
        context.restore()

    @staticmethod
    def _draw_text_box(context: cairo.Context, item) -> None:
        context.save()
        context.set_source_rgba(0.04, 0.08, 0.11, 0.92)
        context.rectangle(item.x, item.y, item.width, item.height)
        context.fill()
        context.set_source_rgba(0.30, 0.65, 0.73, 0.95)
        context.set_line_width(1.2)
        context.rectangle(item.x, item.y, item.width, item.height)
        context.stroke()

        buffer = item.buffer
        text = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), True)
        if getattr(item, "title", ""):
            context.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
            context.set_source_rgb(0.92, 0.96, 1.0)
            context.set_font_size(13)
            context.move_to(item.x + 8, item.y + 17)
            context.show_text(item.title)
            text_y = item.y + 34
        else:
            text_y = item.y + 18

        layout = PangoCairo.create_layout(context)
        layout.set_width(max(1, int((item.width - 16) * Pango.SCALE)))
        layout.set_wrap(Pango.WrapMode.WORD_CHAR)
        layout.set_text(text or "", -1)
        font = Pango.FontDescription("Sans 14")
        layout.set_font_description(font)
        context.move_to(item.x + 8, text_y)
        context.set_source_rgb(0.92, 0.94, 0.97)
        PangoCairo.update_layout(context, layout)
        PangoCairo.show_layout(context, layout)
        context.restore()

    @staticmethod
    def _draw_graph_item(context: cairo.Context, item) -> None:
        node = item.node
        context.save()
        context.translate(item.x, item.y)
        context.set_line_width(node.stroke_width)
        width, height = node.width * item.scale, node.height * item.scale
        context.scale(width / node.width, height / node.height)
        GraphNodeItem._append_shape(context, node)
        context.set_source_rgba(*node.fill_color)
        context.fill_preserve()
        context.set_source_rgba(*node.stroke_color)
        context.stroke()
        context.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        context.set_source_rgba(*node.text_color)
        lines = node.text_lines or ()
        if not lines:
            lines = (
                GraphTextLine(item.title, 12, node.height * 0.42),
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
    def _draw_shape_item(context: cairo.Context, item) -> None:
        context.save()
        context.translate(item.x, item.y)
        item.shape.draw(context, item.width, item.height, item.color, item.rotation)
        if getattr(item, "title", ""):
            context.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
            context.set_source_rgb(*item.color)
            context.set_font_size(max(9, min(14, item.height * 0.14)))
            extents = context.text_extents(item.title)
            context.move_to((item.width - extents.width) / 2 - extents.x_bearing, item.height / 2 + extents.height / 2)
            context.show_text(item.title)
        context.restore()

    @staticmethod
    def _draw_import_item(context: cairo.Context, item) -> None:
        context.save()
        context.set_source_rgba(0.10, 0.13, 0.16, 0.96)
        context.rectangle(item.x, item.y, item.WIDTH, item.HEIGHT)
        context.fill()
        context.rectangle(item.x, item.y, item.WIDTH, item.HEIGHT)
        context.set_source_rgba(0.35, 0.65, 0.78, 0.8)
        context.set_line_width(1)
        context.stroke()

        if item.mime_type.startswith("image/"):
            try:
                image = cairo.ImageSurface.create_from_png(str(item.path)) if item.path.suffix.lower() == ".png" else None
                if image is None:
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(item.path), 136, 56, True)
                    from gi.repository import Gdk
                    Gdk.cairo_set_source_pixbuf(context, pixbuf, item.x + 8, item.y + 6)
                    context.paint()
                else:
                    scale = min(136 / image.get_width(), 56 / image.get_height())
                    context.translate(item.x + 8, item.y + 6)
                    context.scale(scale, scale)
                    context.set_source_surface(image, 0, 0)
                    context.paint()
            except (GLib.Error, OSError, cairo.Error):
                pass

        context.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        context.set_source_rgb(0.92, 0.94, 0.97)
        context.set_font_size(8)
        name = item.display_name
        extents = context.text_extents(name)
        max_width = item.WIDTH - 16
        if extents.width > max_width:
            while len(name) > 2 and context.text_extents(name + "...").width > max_width:
                name = name[:-1]
            name += "..."
        context.move_to(item.x + 8, item.y + item.HEIGHT - 10)
        context.show_text(name)
        context.restore()
