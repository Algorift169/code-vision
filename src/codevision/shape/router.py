from .base import DiagramShape, ellipse, rounded_rectangle


class Router(DiagramShape):
    shape_id = "router"
    name = "Router"
    purpose = "Routes traffic between networks or endpoints."

    def build_path(self, context, width: float, height: float) -> None:
        rounded_rectangle(
            context, width * 0.12, height * 0.46, width * 0.76, height * 0.34,
            height * 0.12,
        )
        context.move_to(width * 0.32, height * 0.46)
        context.line_to(width * 0.24, height * 0.2)
        context.move_to(width * 0.68, height * 0.46)
        context.line_to(width * 0.76, height * 0.2)

    def draw_details(self, context, width: float, height: float, color) -> None:
        for x in (0.28, 0.5, 0.72):
            ellipse(context, width * x, height * 0.63, width * 0.025, height * 0.04)
        context.move_to(width * 0.34, height * 0.32)
        context.line_to(width * 0.46, height * 0.32)
        context.line_to(width * 0.42, height * 0.28)
        context.move_to(width * 0.66, height * 0.32)
        context.line_to(width * 0.54, height * 0.32)
        context.line_to(width * 0.58, height * 0.28)
        context.set_source_rgb(*color)
        context.stroke()
