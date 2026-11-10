from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SourceLocation:
    start_line: int
    start_column: int
    end_line: int
    end_column: int
    start_byte: int
    end_byte: int

    @property
    def has_range(self) -> bool:
        return self.end_byte > self.start_byte
