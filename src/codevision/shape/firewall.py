from .base import DiagramShape


class Firewall(DiagramShape):
    shape_id = "firewall"
    name = "Firewall"
    purpose = "Represents network traffic protection."

    def build_path(self, context, width: float, height: float) -> None:
        context.rectangle(width * 0.08, height * 0.18, width * 0.84, height * 0.64)

    def draw_details(self, context, width: float, height: float, color) -> None:
        for y in (0.4, 0.62):
            context.move_to(width * 0.08, height * y)
            context.line_to(width * 0.92, height * y)
        for x in (0.35, 0.65):
            context.move_to(width * x, height * 0.18)
            context.line_to(width * x, height * 0.4)
            context.move_to(width * (1.0 - x), height * 0.4)
            context.line_to(width * (1.0 - x), height * 0.62)
            context.move_to(width * x, height * 0.62)
            context.line_to(width * x, height * 0.82)
        context.set_line_width(max(1.0, min(width, height) * 0.025))
        context.set_source_rgb(*color)
        context.stroke()
