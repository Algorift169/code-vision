from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class FunctionComplexity:
    name: str
    file_path: Path | None = None
    language: str = "unknown"
    line: int = 1
    cyclomatic: int = 1
    cognitive: int = 0
    time_complexity: str = "O(1)"
    space_complexity: str = "O(1)"
    maintainability: float | None = None
    halstead_volume: float | None = None
    risk: str = "low"
    explanation: str = ""
    evidence: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ComplexityReport:
    file_path: Path | None
    language: str
    functions: list[FunctionComplexity] = field(default_factory=list)
    total_cyclomatic: int = 0
    average_cyclomatic: float = 0.0
    total_cognitive: int = 0
    average_cognitive: float = 0.0
    hotspots: list[FunctionComplexity] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def highest_complexity(self) -> FunctionComplexity | None:
        return max(self.functions, key=lambda item: item.cyclomatic, default=None)

    @property
    def total_functions(self) -> int:
        return len(self.functions)


__all__ = ["ComplexityReport", "FunctionComplexity"]
