from .base import DiagramShape, polygon


class InputOutput(DiagramShape):
    shape_id = "input-output"
    name = "Input / Output"
    purpose = "Represents data entering or leaving a system."

    def build_path(self, context, width: float, height: float) -> None:
        polygon(
            context,
            (
                (width * 0.24, height * 0.14),
                (width * 0.94, height * 0.14),
                (width * 0.76, height * 0.86),
                (width * 0.06, height * 0.86),
            ),
        )
