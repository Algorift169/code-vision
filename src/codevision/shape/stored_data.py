from .base import DiagramShape


class StoredData(DiagramShape):
    shape_id = "stored-data"
    name = "Stored Data"
    purpose = "Represents information saved for later use."

    def build_path(self, context, width: float, height: float) -> None:
        context.move_to(width * 0.16, height * 0.14)
        context.line_to(width * 0.84, height * 0.14)
        context.line_to(width * 0.84, height * 0.68)
        context.curve_to(
            width * 0.84, height * 0.92, width * 0.16, height * 0.92,
            width * 0.16, height * 0.68,
        )
        context.close_path()
        context.move_to(width * 0.16, height * 0.62)
        context.curve_to(
            width * 0.16, height * 0.84, width * 0.84, height * 0.84,
            width * 0.84, height * 0.62,
        )
