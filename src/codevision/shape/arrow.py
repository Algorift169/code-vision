import math

from .base import DiagramShape, polygon


class Arrow(DiagramShape):
    shape_id = "arrow"
    name = "Arrow"
    purpose = "Indicates the direction of flow or movement."

    def build_path(self, context, width: float, height: float) -> None:
        self.build_rotated_path(context, width, height, 0.0)

    def build_rotated_path(
        self,
        context,
        width: float,
        height: float,
        rotation: float,
    ) -> None:
        center_x, center_y = width / 2, height / 2
        direction_x, direction_y = math.cos(rotation), math.sin(rotation)
        perpendicular_x, perpendicular_y = -direction_y, direction_x
        margin = min(width, height) * 0.2
        limits = []
        if abs(direction_x) > 1e-6:
            limits.append((width / 2 - margin) / abs(direction_x))
        if abs(direction_y) > 1e-6:
            limits.append((height / 2 - margin) / abs(direction_y))
        half_length = min(limits)
        half_shaft = min(width, height) * 0.08
        half_head = min(width, height) * 0.2
        head_length = min(width, height) * 0.24
        tip_x = center_x + direction_x * half_length
        tip_y = center_y + direction_y * half_length
        shoulder_x = tip_x - direction_x * head_length
        shoulder_y = tip_y - direction_y * head_length
        shaft_end_x = shoulder_x - direction_x * half_shaft
        shaft_end_y = shoulder_y - direction_y * half_shaft
        tail_x = center_x - direction_x * half_length
        tail_y = center_y - direction_y * half_length

        polygon(
            context,
            (
                (
                    tail_x + perpendicular_x * half_shaft,
                    tail_y + perpendicular_y * half_shaft,
                ),
                (
                    shaft_end_x + perpendicular_x * half_shaft,
                    shaft_end_y + perpendicular_y * half_shaft,
                ),
                (
                    shoulder_x + perpendicular_x * half_head,
                    shoulder_y + perpendicular_y * half_head,
                ),
                (tip_x, tip_y),
                (
                    shoulder_x - perpendicular_x * half_head,
                    shoulder_y - perpendicular_y * half_head,
                ),
                (
                    shaft_end_x - perpendicular_x * half_shaft,
                    shaft_end_y - perpendicular_y * half_shaft,
                ),
                (
                    tail_x - perpendicular_x * half_shaft,
                    tail_y - perpendicular_y * half_shaft,
                ),
            ),
        )
