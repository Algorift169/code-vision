from .base import DiagramShape, polygon


class Preparation(DiagramShape):
    shape_id = "preparation"
    name = "Preparation"
    purpose = "Represents initialization or setup."

    def build_path(self, context, width: float, height: float) -> None:
        polygon(
            context,
            (
                (width * 0.24, height * 0.12),
                (width * 0.76, height * 0.12),
                (width * 0.94, height * 0.5),
                (width * 0.76, height * 0.88),
                (width * 0.24, height * 0.88),
                (width * 0.06, height * 0.5),
            ),
        )
