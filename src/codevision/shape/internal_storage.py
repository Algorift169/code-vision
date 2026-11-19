from .base import DiagramShape


class InternalStorage(DiagramShape):
    shape_id = "internal-storage"
    name = "Internal Storage"
    purpose = "Represents data held in internal memory."

    def build_path(self, context, width: float, height: float) -> None:
        context.rectangle(width * 0.08, height * 0.16, width * 0.84, height * 0.68)
        context.move_to(width * 0.27, height * 0.16)
        context.line_to(width * 0.27, height * 0.84)

    def draw_details(self, context, width: float, height: float, color) -> None:
        context.move_to(width * 0.4, height * 0.38)
        context.line_to(width * 0.8, height * 0.38)
        context.move_to(width * 0.4, height * 0.62)
        context.line_to(width * 0.8, height * 0.62)
        context.set_source_rgb(*color)
        context.stroke()
