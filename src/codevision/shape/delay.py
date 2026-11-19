from .base import DiagramShape


class Delay(DiagramShape):
    shape_id = "delay"
    name = "Delay"
    purpose = "Represents a waiting period in a process."

    def build_path(self, context, width: float, height: float) -> None:
        context.move_to(width * 0.18, height * 0.14)
        context.line_to(width * 0.52, height * 0.14)
        context.curve_to(
            width * 0.9, height * 0.14, width * 0.9, height * 0.86,
            width * 0.52, height * 0.86,
        )
        context.line_to(width * 0.18, height * 0.86)
        context.close_path()
