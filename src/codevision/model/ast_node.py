from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator

from .source_location import SourceLocation


@dataclass(slots=True)
class ASTNode:
    node_id: str
    node_type: str
    display_name: str
    source_text: str
    location: SourceLocation
    parent_id: str | None = None
    children: list[ASTNode] = field(default_factory=list)
    has_error: bool = False
    is_missing: bool = False

    def walk(self) -> Iterator[ASTNode]:
        stack = [self]
        while stack:
            node = stack.pop()
            yield node
            stack.extend(reversed(node.children))

    @property
    def child_count(self) -> int:
        return len(self.children)
