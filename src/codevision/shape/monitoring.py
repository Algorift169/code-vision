from .base import DiagramShape, rounded_rectangle


class Monitoring(DiagramShape):
    shape_id = "monitoring"
    name = "Monitoring"
    purpose = "Represents system health and performance monitoring."

    def build_path(self, context, width: float, height: float) -> None:
        rounded_rectangle(
            context, width * 0.08, height * 0.12, width * 0.84, height * 0.62,
            height * 0.06,
        )
        context.move_to(width * 0.5, height * 0.74)
        context.line_to(width * 0.5, height * 0.86)
        context.move_to(width * 0.32, height * 0.86)
        context.line_to(width * 0.68, height * 0.86)

    def draw_details(self, context, width: float, height: float, color) -> None:
        context.move_to(width * 0.18, height * 0.5)
        context.line_to(width * 0.34, height * 0.5)
        context.line_to(width * 0.42, height * 0.34)
        context.line_to(width * 0.54, height * 0.62)
        context.line_to(width * 0.64, height * 0.42)
        context.line_to(width * 0.82, height * 0.42)
        context.set_source_rgb(*color)
        context.stroke()
