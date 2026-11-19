from .base import DiagramShape, ellipse


class LoadGenerator(DiagramShape):
    shape_id = "load-generator"
    name = "Load Generator"
    purpose = "Generates traffic or requests for a system."

    def build_path(self, context, width: float, height: float) -> None:
        context.move_to(width * 0.16, height * 0.76)
        context.curve_to(
            width * 0.16, height * 0.24, width * 0.84, height * 0.24,
            width * 0.84, height * 0.76,
        )
        context.move_to(width * 0.16, height * 0.76)
        context.line_to(width * 0.84, height * 0.76)

    def draw_details(self, context, width: float, height: float, color) -> None:
        context.move_to(width * 0.5, height * 0.66)
        context.line_to(width * 0.69, height * 0.43)
        ellipse(context, width * 0.5, height * 0.66, width * 0.035, height * 0.05)
        context.set_source_rgb(*color)
        context.stroke()
