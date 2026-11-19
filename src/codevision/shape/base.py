from __future__ import annotations

from abc import ABC, abstractmethod

import cairo

Color = tuple[float, float, float]


class DiagramShape(ABC):
    """Reusable path and styling contract for a system-design shape."""

    shape_id: str
    name: str
    purpose: str
    filled = True

    def draw(
        self,
        context,
        width: float,
        height: float,
        color: Color,
        rotation: float = 0.0,
    ) -> None:
        context.save()
        context.set_line_width(max(1.5, min(width, height) * 0.035))
        context.set_line_cap(cairo.LINE_CAP_ROUND)
        context.set_line_join(cairo.LINE_JOIN_ROUND)
        self.build_rotated_path(context, width, height, rotation)
        if self.filled:
            context.set_source_rgba(*color, 0.18)
            context.fill_preserve()
        context.set_source_rgb(*color)
        context.stroke()
        self.draw_details(context, width, height, color)
        context.restore()

    @abstractmethod
    def build_path(self, context, width: float, height: float) -> None:
        """Append this shape's outline to a Cairo path."""

    def build_rotated_path(
        self,
        context,
        width: float,
        height: float,
        rotation: float,
    ) -> None:
        context.translate(width / 2, height / 2)
        context.rotate(rotation)
        context.translate(-width / 2, -height / 2)
        self.build_path(context, width, height)

    def draw_details(
        self,
        context,
        width: float,
        height: float,
        color: Color,
    ) -> None:
        return


def rounded_rectangle(
    context,
    x: float,
    y: float,
    width: float,
    height: float,
    radius: float,
) -> None:
    radius = min(radius, width / 2, height / 2)
    context.move_to(x + radius, y)
    context.line_to(x + width - radius, y)
    context.arc(
        x + width - radius, y + radius, radius, -1.57079632679, 0
    )
    context.line_to(x + width, y + height - radius)
    context.arc(
        x + width - radius,
        y + height - radius,
        radius,
        0,
        1.57079632679,
    )
    context.line_to(x + radius, y + height)
    context.arc(
        x + radius,
        y + height - radius,
        radius,
        1.57079632679,
        3.14159265359,
    )
    context.line_to(x, y + radius)
    context.arc(
        x + radius, y + radius, radius, 3.14159265359, 4.71238898038
    )
    context.close_path()


def polygon(context, points: tuple[tuple[float, float], ...]) -> None:
    if not points:
        return
    context.move_to(*points[0])
    for point in points[1:]:
        context.line_to(*point)
    context.close_path()


def ellipse(
    context,
    center_x: float,
    center_y: float,
    radius_x: float,
    radius_y: float,
) -> None:
    control = 0.5522847498
    context.move_to(center_x + radius_x, center_y)
    context.curve_to(
        center_x + radius_x,
        center_y + control * radius_y,
        center_x + control * radius_x,
        center_y + radius_y,
        center_x,
        center_y + radius_y,
    )
    context.curve_to(
        center_x - control * radius_x,
        center_y + radius_y,
        center_x - radius_x,
        center_y + control * radius_y,
        center_x - radius_x,
        center_y,
    )
    context.curve_to(
        center_x - radius_x,
        center_y - control * radius_y,
        center_x - control * radius_x,
        center_y - radius_y,
        center_x,
        center_y - radius_y,
    )
    context.curve_to(
        center_x + control * radius_x,
        center_y - radius_y,
        center_x + radius_x,
        center_y - control * radius_y,
        center_x + radius_x,
        center_y,
    )
    context.close_path()


def cylinder_path(
    context,
    x: float,
    y: float,
    width: float,
    height: float,
) -> None:
    radius_x = width / 2
    ellipse_height = min(height * 0.15, width * 0.18)
    control = 0.5522847498
    center_x = x + radius_x
    top_center_y = y + ellipse_height
    bottom_center_y = y + height - ellipse_height

    context.move_to(x, top_center_y)
    context.curve_to(
        x,
        top_center_y - control * ellipse_height,
        center_x - control * radius_x,
        y,
        center_x,
        y,
    )
    context.curve_to(
        center_x + control * radius_x,
        y,
        x + width,
        top_center_y - control * ellipse_height,
        x + width,
        top_center_y,
    )
    context.line_to(x + width, bottom_center_y)
    context.curve_to(
        x + width,
        bottom_center_y + control * ellipse_height,
        center_x + control * radius_x,
        y + height,
        center_x,
        y + height,
    )
    context.curve_to(
        center_x - control * radius_x,
        y + height,
        x,
        bottom_center_y + control * ellipse_height,
        x,
        bottom_center_y,
    )
    context.close_path()

    context.move_to(x + width, top_center_y)
    context.curve_to(
        x + width,
        top_center_y + control * ellipse_height,
        center_x + control * radius_x,
        top_center_y + ellipse_height,
        center_x,
        top_center_y + ellipse_height,
    )
    context.curve_to(
        center_x - control * radius_x,
        top_center_y + ellipse_height,
        x,
        top_center_y + control * ellipse_height,
        x,
        top_center_y,
    )
    context.close_path()


__all__ = [
    "DiagramShape",
    "cylinder_path",
    "ellipse",
    "polygon",
    "rounded_rectangle",
]
