from .base import DiagramShape, rounded_rectangle


class Client(DiagramShape):
    shape_id = "client"
    name = "Client"
    purpose = "Represents a client application that makes requests."

    def build_path(self, context, width: float, height: float) -> None:
        rounded_rectangle(
            context, width * 0.12, height * 0.12, width * 0.76, height * 0.6,
            height * 0.08,
        )
        context.move_to(width * 0.5, height * 0.72)
        context.line_to(width * 0.5, height * 0.84)
        context.move_to(width * 0.34, height * 0.84)
        context.line_to(width * 0.66, height * 0.84)

    def draw_details(self, context, width: float, height: float, color) -> None:
        context.move_to(width * 0.2, height * 0.6)
        context.line_to(width * 0.8, height * 0.6)
        context.set_source_rgb(*color)
        context.stroke()
