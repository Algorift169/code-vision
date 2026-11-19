from .base import DiagramShape, ellipse, rounded_rectangle


class Cache(DiagramShape):
    shape_id = "cache"
    name = "Cache"
    purpose = "Represents quickly accessible cached data."

    def build_path(self, context, width: float, height: float) -> None:
        rounded_rectangle(
            context, width * 0.12, height * 0.18, width * 0.76, height * 0.64,
            height * 0.1,
        )
        context.move_to(width * 0.2, height * 0.37)
        context.line_to(width * 0.8, height * 0.37)

    def draw_details(self, context, width: float, height: float, color) -> None:
        ellipse(context, width * 0.34, height * 0.59, width * 0.09, height * 0.11)
        context.move_to(width * 0.34, height * 0.59)
        context.line_to(width * 0.34, height * 0.52)
        context.move_to(width * 0.34, height * 0.59)
        context.line_to(width * 0.39, height * 0.62)
        context.move_to(width * 0.52, height * 0.55)
        context.line_to(width * 0.72, height * 0.55)
        context.move_to(width * 0.52, height * 0.66)
        context.line_to(width * 0.72, height * 0.66)
        context.set_source_rgb(*color)
        context.stroke()
