from .base import DiagramShape, ellipse


class Network(DiagramShape):
    shape_id = "network"
    name = "Network"
    purpose = "Represents a connected network segment."

    def build_path(self, context, width: float, height: float) -> None:
        points = (
            (width * 0.2, height * 0.28),
            (width * 0.8, height * 0.28),
            (width * 0.5, height * 0.76),
            (width * 0.2, height * 0.28),
        )
        for start, end in zip(points, points[1:]):
            context.move_to(*start)
            context.line_to(*end)

    def draw_details(self, context, width: float, height: float, color) -> None:
        for x, y in ((0.2, 0.28), (0.8, 0.28), (0.5, 0.76)):
            ellipse(context, width * x, height * y, width * 0.09, height * 0.13)
        context.set_source_rgba(0.18, 0.18, 0.18, 1)
        context.fill_preserve()
        context.set_source_rgb(*color)
        context.stroke()
