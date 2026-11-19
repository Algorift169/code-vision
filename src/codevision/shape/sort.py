from .base import DiagramShape


class Sort(DiagramShape):
    shape_id = "sort"
    name = "Sort"
    purpose = "Represents ordering or sorting data."

    def build_path(self, context, width: float, height: float) -> None:
        context.move_to(width * 0.08, height * 0.16)
        context.line_to(width * 0.92, height * 0.16)
        context.line_to(width * 0.78, height * 0.84)
        context.line_to(width * 0.22, height * 0.84)
        context.close_path()

    def draw_details(self, context, width: float, height: float, color) -> None:
        for index, bar_width in enumerate((0.42, 0.28, 0.14)):
            y = height * (0.34 + index * 0.17)
            context.move_to(width * 0.5 - width * bar_width / 2, y)
            context.line_to(width * 0.5 + width * bar_width / 2, y)
        context.set_source_rgb(*color)
        context.stroke()
