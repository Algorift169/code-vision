from .base import DiagramShape, rounded_rectangle


class Terminal(DiagramShape):
    shape_id = "terminal"
    name = "Terminal"
    purpose = "Marks the start or end of a workflow."

    def build_path(self, context, width: float, height: float) -> None:
        rounded_rectangle(
            context, width * 0.08, height * 0.16, width * 0.84, height * 0.68,
            height * 0.34,
        )
