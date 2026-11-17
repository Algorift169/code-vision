from __future__ import annotations

import math
from collections.abc import Callable


class SpaceZoom:
    """Track and apply the Space board's zoom level."""

    MIN_SCALE = 0.4
    MAX_SCALE = 3.0
    STEP = 1.25

    def __init__(self, on_changed: Callable[[], None]) -> None:
        self.scale = 1.0
        self._on_changed = on_changed

    def zoom_in(self) -> None:
        self._set_scale(min(self.MAX_SCALE, self.scale * self.STEP))

    def zoom_out(self) -> None:
        self._set_scale(max(self.MIN_SCALE, self.scale / self.STEP))

    def to_board(self, x: float, y: float) -> tuple[float, float]:
        return x / self.scale, y / self.scale

    def to_pixels(self, size: int) -> int:
        return math.ceil(size * self.scale)

    def scale_context(self, context) -> None:
        context.scale(self.scale, self.scale)

    def _set_scale(self, scale: float) -> None:
        if scale == self.scale:
            return
        self.scale = scale
        self._on_changed()
