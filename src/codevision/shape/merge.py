from .base import DiagramShape, polygon


class Merge(DiagramShape):
    shape_id = "merge"
    name = "Merge"
    purpose = "Combines multiple flows into one."

    def build_path(self, context, width: float, height: float) -> None:
        polygon(
            context,
            (
                (width * 0.08, height * 0.2),
                (width * 0.92, height * 0.2),
                (width * 0.5, height * 0.88),
            ),
        )
