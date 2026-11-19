from .base import DiagramShape, ellipse


class EventBus(DiagramShape):
    shape_id = "event-bus"
    name = "Event Bus"
    purpose = "Distributes events between system components."

    def build_path(self, context, width: float, height: float) -> None:
        context.move_to(width * 0.14, height * 0.5)
        context.line_to(width * 0.86, height * 0.5)
        context.move_to(width * 0.3, height * 0.5)
        context.line_to(width * 0.3, height * 0.2)
        context.move_to(width * 0.5, height * 0.5)
        context.line_to(width * 0.5, height * 0.8)
        context.move_to(width * 0.7, height * 0.5)
        context.line_to(width * 0.7, height * 0.2)

    def draw_details(self, context, width: float, height: float, color) -> None:
        for x, y in ((0.3, 0.2), (0.5, 0.8), (0.7, 0.2)):
            ellipse(context, width * x, height * y, width * 0.07, height * 0.1)
        context.set_source_rgb(*color)
        context.stroke()
