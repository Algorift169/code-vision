from .base import DiagramShape, rounded_rectangle


class MessageBroker(DiagramShape):
    shape_id = "message-broker"
    name = "Message Broker"
    purpose = "Routes and manages messages between services."

    def build_path(self, context, width: float, height: float) -> None:
        rounded_rectangle(
            context, width * 0.12, height * 0.18, width * 0.76, height * 0.64,
            height * 0.08,
        )
        context.move_to(width * 0.24, height * 0.36)
        context.line_to(width * 0.76, height * 0.36)
        context.move_to(width * 0.24, height * 0.64)
        context.line_to(width * 0.76, height * 0.64)

    def draw_details(self, context, width: float, height: float, color) -> None:
        for x in (0.32, 0.5, 0.68):
            context.move_to(width * x, height * 0.36)
            context.line_to(width * x, height * 0.64)
        context.set_source_rgb(*color)
        context.stroke()
