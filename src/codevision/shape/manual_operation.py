from .base import DiagramShape, polygon


class ManualOperation(DiagramShape):
    shape_id = "manual-operation"
    name = "Manual Operation"
    purpose = "Represents a human-performed operation."

    def build_path(self, context, width: float, height: float) -> None:
        polygon(
            context,
            (
                (width * 0.08, height * 0.16),
                (width * 0.92, height * 0.16),
                (width * 0.76, height * 0.86),
                (width * 0.24, height * 0.86),
            ),
        )
