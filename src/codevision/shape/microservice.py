from .base import DiagramShape, rounded_rectangle


class Microservice(DiagramShape):
    shape_id = "microservice"
    name = "Microservice"
    purpose = "Represents a small, independently deployable service."

    def build_path(self, context, width: float, height: float) -> None:
        rounded_rectangle(
            context, width * 0.14, height * 0.12, width * 0.72, height * 0.76,
            height * 0.12,
        )

    def draw_details(self, context, width: float, height: float, color) -> None:
        for x, y in (
            (0.38, 0.38), (0.62, 0.38), (0.38, 0.62), (0.62, 0.62),
        ):
            context.arc(width * x, height * y, min(width, height) * 0.045, 0, 6.28318530718)
        context.set_source_rgb(*color)
        context.stroke()
