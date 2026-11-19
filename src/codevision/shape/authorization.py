from .base import DiagramShape, polygon


class Authorization(DiagramShape):
    shape_id = "authorization"
    name = "Authorization"
    purpose = "Represents checking permission to access a resource."

    def build_path(self, context, width: float, height: float) -> None:
        polygon(
            context,
            (
                (width * 0.5, height * 0.08),
                (width * 0.88, height * 0.22),
                (width * 0.82, height * 0.62),
                (width * 0.5, height * 0.9),
                (width * 0.18, height * 0.62),
                (width * 0.12, height * 0.22),
            ),
        )

    def draw_details(self, context, width: float, height: float, color) -> None:
        context.move_to(width * 0.32, height * 0.5)
        context.line_to(width * 0.46, height * 0.64)
        context.line_to(width * 0.7, height * 0.36)
        context.set_source_rgb(*color)
        context.stroke()
