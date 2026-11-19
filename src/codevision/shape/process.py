from .base import DiagramShape


class Process(DiagramShape):
    shape_id = "process"
    name = "Process"
    purpose = "Represents an operation or computation."

    def build_path(self, context, width: float, height: float) -> None:
        context.rectangle(width * 0.08, height * 0.16, width * 0.84, height * 0.68)
