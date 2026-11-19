from .base import DiagramShape


class TapeStorage(DiagramShape):
    shape_id = "tape-storage"
    name = "Tape Storage"
    purpose = "Represents sequential tape-based storage."

    def build_path(self, context, width: float, height: float) -> None:
        context.move_to(width * 0.08, height * 0.24)
        context.curve_to(
            width * 0.24, height * 0.06, width * 0.36, height * 0.42,
            width * 0.52, height * 0.24,
        )
        context.curve_to(
            width * 0.68, height * 0.06, width * 0.8, height * 0.42,
            width * 0.92, height * 0.24,
        )
        context.line_to(width * 0.92, height * 0.76)
        context.curve_to(
            width * 0.76, height * 0.94, width * 0.64, height * 0.58,
            width * 0.48, height * 0.76,
        )
        context.curve_to(
            width * 0.32, height * 0.94, width * 0.2, height * 0.58,
            width * 0.08, height * 0.76,
        )
        context.close_path()
