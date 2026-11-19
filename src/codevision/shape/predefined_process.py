from .base import DiagramShape


class PredefinedProcess(DiagramShape):
    shape_id = "predefined-process"
    name = "Predefined Process"
    purpose = "Represents a reusable routine defined elsewhere."

    def build_path(self, context, width: float, height: float) -> None:
        context.rectangle(width * 0.08, height * 0.14, width * 0.84, height * 0.72)
        context.move_to(width * 0.2, height * 0.14)
        context.line_to(width * 0.2, height * 0.86)
        context.move_to(width * 0.8, height * 0.14)
        context.line_to(width * 0.8, height * 0.86)
