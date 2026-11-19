from .base import DiagramShape, rounded_rectangle


class Switch(DiagramShape):
    shape_id = "switch"
    name = "Switch"
    purpose = "Connects devices within a network."

    def build_path(self, context, width: float, height: float) -> None:
        rounded_rectangle(
            context, width * 0.08, height * 0.26, width * 0.84, height * 0.5,
            height * 0.1,
        )

    def draw_details(self, context, width: float, height: float, color) -> None:
        for index in range(4):
            x = width * (0.24 + index * 0.16)
            context.rectangle(x, height * 0.42, width * 0.08, height * 0.16)
        context.set_source_rgb(*color)
        context.stroke()
