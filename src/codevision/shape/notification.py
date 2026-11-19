from .base import DiagramShape, ellipse


class Notification(DiagramShape):
    shape_id = "notification"
    name = "Notification"
    purpose = "Represents a notification delivered to a user."

    def build_path(self, context, width: float, height: float) -> None:
        context.move_to(width * 0.2, height * 0.72)
        context.curve_to(
            width * 0.3, height * 0.6, width * 0.28, height * 0.38,
            width * 0.34, height * 0.28,
        )
        context.curve_to(
            width * 0.42, height * 0.12, width * 0.58, height * 0.12,
            width * 0.66, height * 0.28,
        )
        context.curve_to(
            width * 0.72, height * 0.38, width * 0.7, height * 0.6,
            width * 0.8, height * 0.72,
        )
        context.close_path()
        context.move_to(width * 0.2, height * 0.72)
        context.line_to(width * 0.8, height * 0.72)

    def draw_details(self, context, width: float, height: float, color) -> None:
        context.move_to(width * 0.42, height * 0.82)
        context.curve_to(
            width * 0.45, height * 0.94, width * 0.55, height * 0.94,
            width * 0.58, height * 0.82,
        )
        context.set_source_rgb(*color)
        context.stroke()
