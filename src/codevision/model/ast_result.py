from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .ast_node import ASTNode


@dataclass(frozen=True, slots=True)
class ASTResult:
    root: ASTNode
    language: str
    file_path: Path | None
    node_count: int
    max_depth: int
    parse_duration_ms: float
    syntax_error_count: int
    errors: tuple[str, ...] = ()

    @property
    def succeeded(self) -> bool:
        return self.syntax_error_count == 0 and not self.errors

    @property
    def is_partial(self) -> bool:
        return not self.succeeded
