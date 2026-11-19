from .base import DiagramShape, polygon


class OffPageConnector(DiagramShape):
    shape_id = "off-page-connector"
    name = "Off-Page Connector"
    purpose = "Connects a flow to another diagram page."

    def build_path(self, context, width: float, height: float) -> None:
        polygon(
            context,
            (
                (width * 0.12, height * 0.12),
                (width * 0.88, height * 0.12),
                (width * 0.88, height * 0.62),
                (width * 0.5, height * 0.9),
                (width * 0.12, height * 0.62),
            ),
        )
