from .base import DiagramShape, ellipse


class Connector(DiagramShape):
    shape_id = "connector"
    name = "Connector"
    purpose = "Connects separated sections of a flowchart."

    def build_path(self, context, width: float, height: float) -> None:
        ellipse(context, width / 2, height / 2, width * 0.34, height * 0.34)
