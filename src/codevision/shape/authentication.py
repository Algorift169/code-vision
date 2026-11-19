from .base import DiagramShape, ellipse


class Authentication(DiagramShape):
    shape_id = "authentication"
    name = "Authentication"
    purpose = "Represents verifying a user's identity."

    def build_path(self, context, width: float, height: float) -> None:
        ellipse(context, width * 0.38, height * 0.32, width * 0.13, height * 0.17)
        context.move_to(width * 0.14, height * 0.84)
        context.curve_to(
            width * 0.14, height * 0.58, width * 0.62, height * 0.58,
            width * 0.62, height * 0.84,
        )
        context.close_path()
        ellipse(context, width * 0.73, height * 0.61, width * 0.11, height * 0.14)

    def draw_details(self, context, width: float, height: float, color) -> None:
        context.move_to(width * 0.73, height * 0.61)
        context.line_to(width * 0.73, height * 0.69)
        context.set_source_rgb(*color)
        context.stroke()
