from .base import DiagramShape, polygon


class ManualInput(DiagramShape):
    shape_id = "manual-input"
    name = "Manual Input"
    purpose = "Represents user-provided input."

    def build_path(self, context, width: float, height: float) -> None:
        polygon(
            context,
            (
                (width * 0.08, height * 0.3),
                (width * 0.92, height * 0.12),
                (width * 0.92, height * 0.88),
                (width * 0.08, height * 0.88),
            ),
        )
