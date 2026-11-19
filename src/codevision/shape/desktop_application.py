from .base import DiagramShape, rounded_rectangle


class DesktopApplication(DiagramShape):
    shape_id = "desktop-application"
    name = "Desktop Application"
    purpose = "Represents software running as a desktop application."

    def build_path(self, context, width: float, height: float) -> None:
        rounded_rectangle(
            context, width * 0.1, height * 0.12, width * 0.8, height * 0.62,
            height * 0.06,
        )
        context.move_to(width * 0.5, height * 0.74)
        context.line_to(width * 0.5, height * 0.86)
        context.move_to(width * 0.32, height * 0.86)
        context.line_to(width * 0.68, height * 0.86)

    def draw_details(self, context, width: float, height: float, color) -> None:
        context.move_to(width * 0.1, height * 0.3)
        context.line_to(width * 0.9, height * 0.3)
        context.set_source_rgb(*color)
        context.stroke()
