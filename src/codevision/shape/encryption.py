from .base import DiagramShape, rounded_rectangle


class Encryption(DiagramShape):
    shape_id = "encryption"
    name = "Encryption"
    purpose = "Represents data protected by encryption."

    def build_path(self, context, width: float, height: float) -> None:
        context.move_to(width * 0.3, height * 0.48)
        context.line_to(width * 0.3, height * 0.32)
        context.curve_to(
            width * 0.3, height * 0.08, width * 0.7, height * 0.08,
            width * 0.7, height * 0.32,
        )
        context.line_to(width * 0.7, height * 0.48)
        rounded_rectangle(
            context, width * 0.18, height * 0.44, width * 0.64, height * 0.46,
            height * 0.06,
        )

    def draw_details(self, context, width: float, height: float, color) -> None:
        context.arc(width * 0.5, height * 0.63, width * 0.045, 0, 6.28318530718)
        context.move_to(width * 0.5, height * 0.65)
        context.line_to(width * 0.5, height * 0.77)
        context.set_source_rgb(*color)
        context.stroke()
