from .base import DiagramShape, ellipse, rounded_rectangle


class MobileDevice(DiagramShape):
    shape_id = "mobile-device"
    name = "Mobile Device"
    purpose = "Represents a mobile application or device."

    def build_path(self, context, width: float, height: float) -> None:
        rounded_rectangle(
            context, width * 0.32, height * 0.08, width * 0.36, height * 0.84,
            width * 0.07,
        )
        context.move_to(width * 0.38, height * 0.2)
        context.line_to(width * 0.62, height * 0.2)
        context.move_to(width * 0.38, height * 0.78)
        context.line_to(width * 0.62, height * 0.78)
        ellipse(context, width * 0.5, height * 0.85, width * 0.025, height * 0.025)
