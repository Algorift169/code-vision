from .base import DiagramShape, ellipse, rounded_rectangle


class WebBrowser(DiagramShape):
    shape_id = "web-browser"
    name = "Web Browser"
    purpose = "Represents a browser interface for a web application."

    def build_path(self, context, width: float, height: float) -> None:
        rounded_rectangle(
            context, width * 0.08, height * 0.14, width * 0.84, height * 0.72,
            height * 0.08,
        )
        context.move_to(width * 0.08, height * 0.34)
        context.line_to(width * 0.92, height * 0.34)

    def draw_details(self, context, width: float, height: float, color) -> None:
        for x in (0.18, 0.27, 0.36):
            ellipse(context, width * x, height * 0.24, width * 0.025, height * 0.035)
        context.move_to(width * 0.2, height * 0.47)
        context.line_to(width * 0.8, height * 0.47)
        context.move_to(width * 0.2, height * 0.59)
        context.line_to(width * 0.62, height * 0.59)
        context.move_to(width * 0.2, height * 0.71)
        context.line_to(width * 0.7, height * 0.71)
        context.set_source_rgb(*color)
        context.stroke()
