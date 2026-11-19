from .base import DiagramShape, polygon


class Extract(DiagramShape):
    shape_id = "extract"
    name = "Extract"
    purpose = "Separates a branch or item from a flow."

    def build_path(self, context, width: float, height: float) -> None:
        polygon(
            context,
            (
                (width * 0.5, height * 0.12),
                (width * 0.92, height * 0.82),
                (width * 0.08, height * 0.82),
            ),
        )

    def draw_details(self, context, width: float, height: float, color) -> None:
        context.move_to(width * 0.5, height * 0.34)
        context.line_to(width * 0.5, height * 0.68)
        context.set_source_rgb(*color)
        context.stroke()
