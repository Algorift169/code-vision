from .base import DiagramShape, rounded_rectangle


class ApiGateway(DiagramShape):
    shape_id = "api-gateway"
    name = "API Gateway"
    purpose = "Provides a managed entry point that routes API requests."

    def build_path(self, context, width: float, height: float) -> None:
        rounded_rectangle(
            context, width * 0.1, height * 0.14, width * 0.8, height * 0.72,
            height * 0.08,
        )
        context.move_to(width * 0.32, height * 0.14)
        context.line_to(width * 0.32, height * 0.86)
        context.move_to(width * 0.68, height * 0.14)
        context.line_to(width * 0.68, height * 0.86)

    def draw_details(self, context, width: float, height: float, color) -> None:
        context.move_to(width * 0.4, height * 0.5)
        context.line_to(width * 0.6, height * 0.5)
        context.move_to(width * 0.54, height * 0.42)
        context.line_to(width * 0.62, height * 0.5)
        context.line_to(width * 0.54, height * 0.58)
        context.set_source_rgb(*color)
        context.stroke()
