from .base import DiagramShape


class LogCollector(DiagramShape):
    shape_id = "log-collector"
    name = "Log Collector"
    purpose = "Collects application and system logs."

    def build_path(self, context, width: float, height: float) -> None:
        context.rectangle(width * 0.24, height * 0.12, width * 0.64, height * 0.72)
        context.move_to(width * 0.16, height * 0.2)
        context.line_to(width * 0.16, height * 0.76)
        context.line_to(width * 0.24, height * 0.8)
        context.move_to(width * 0.34, height * 0.34)
        context.line_to(width * 0.76, height * 0.34)
        context.move_to(width * 0.34, height * 0.48)
        context.line_to(width * 0.7, height * 0.48)
        context.move_to(width * 0.34, height * 0.62)
        context.line_to(width * 0.76, height * 0.62)
