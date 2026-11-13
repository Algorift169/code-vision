from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..model import ASTNode


@dataclass(slots=True)
class CallGraphNode:
    node_id: str
    name: str
    qualified_name: str = ""
    source_node: ASTNode | None = None
    x: float = 0.0
    y: float = 0.0
    width: float = 184.0
    height: float = 82.0


@dataclass(slots=True)
class CallGraphEdge:
    source_id: str
    target_id: str
    call_sites: list[ASTNode] = field(default_factory=list)

    @property
    def label(self) -> str:
        if not self.call_sites:
            return "call"
        label = self.call_sites[0].source_text.strip() or "call"
        if len(self.call_sites) > 1:
            return f"{label} x{len(self.call_sites)}"
        return label


@dataclass(slots=True)
class CallGraph:
    source_file: Path | None
    language: str
    nodes: list[CallGraphNode] = field(default_factory=list)
    edges: list[CallGraphEdge] = field(default_factory=list)


__all__ = ["CallGraph", "CallGraphEdge", "CallGraphNode"]