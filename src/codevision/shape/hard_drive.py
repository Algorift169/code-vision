from .base import DiagramShape, ellipse, rounded_rectangle


class HardDrive(DiagramShape):
    shape_id = "hard-drive"
    name = "Hard Drive"
    purpose = "Represents persistent disk storage."

    def build_path(self, context, width: float, height: float) -> None:
        rounded_rectangle(
            context, width * 0.08, height * 0.14, width * 0.84, height * 0.72,
            height * 0.1,
        )
        ellipse(context, width * 0.5, height * 0.48, width * 0.2, height * 0.22)
        context.move_to(width * 0.5, height * 0.48)
        context.line_to(width * 0.68, height * 0.7)
        context.move_to(width * 0.22, height * 0.76)
        context.line_to(width * 0.78, height * 0.76)
