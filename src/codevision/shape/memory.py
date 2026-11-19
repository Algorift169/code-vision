from .base import DiagramShape


class Memory(DiagramShape):
    shape_id = "memory"
    name = "Memory"
    purpose = "Represents RAM or working memory."

    def build_path(self, context, width: float, height: float) -> None:
        context.rectangle(width * 0.2, height * 0.22, width * 0.6, height * 0.56)
        for x in (0.3, 0.5, 0.7):
            context.move_to(width * x, height * 0.22)
            context.line_to(width * x, height * 0.1)
            context.move_to(width * x, height * 0.78)
            context.line_to(width * x, height * 0.9)
        for y in (0.34, 0.5, 0.66):
            context.move_to(width * 0.2, height * y)
            context.line_to(width * 0.1, height * y)
            context.move_to(width * 0.8, height * y)
            context.line_to(width * 0.9, height * y)
