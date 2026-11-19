from .base import DiagramShape


class Subprocess(DiagramShape):
    shape_id = "subprocess"
    name = "Subprocess"
    purpose = "Represents a nested process."

    def build_path(self, context, width: float, height: float) -> None:
        context.rectangle(width * 0.08, height * 0.14, width * 0.84, height * 0.72)
        context.move_to(width * 0.24, height * 0.14)
        context.line_to(width * 0.24, height * 0.86)
        context.move_to(width * 0.76, height * 0.14)
        context.line_to(width * 0.76, height * 0.86)
