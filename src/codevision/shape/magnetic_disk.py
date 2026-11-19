from .base import DiagramShape, ellipse


class MagneticDisk(DiagramShape):
    shape_id = "magnetic-disk"
    name = "Magnetic Disk"
    purpose = "Represents rotating magnetic disk storage."

    def build_path(self, context, width: float, height: float) -> None:
        ellipse(context, width * 0.5, height * 0.5, width * 0.4, height * 0.34)
        ellipse(context, width * 0.5, height * 0.5, width * 0.25, height * 0.21)
        ellipse(context, width * 0.5, height * 0.5, width * 0.07, height * 0.06)

    def draw_details(self, context, width: float, height: float, color) -> None:
        context.move_to(width * 0.56, height * 0.5)
        context.line_to(width * 0.84, height * 0.72)
        context.set_source_rgb(*color)
        context.stroke()
