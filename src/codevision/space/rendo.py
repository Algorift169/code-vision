from __future__ import annotations

from .pen import Pen


class Redo:
    def __init__(self, pen: Pen) -> None:
        self._pen = pen

    def execute(self) -> None:
        self._pen.redo()
