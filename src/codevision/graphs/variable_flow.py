from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..model import ASTNode


@dataclass(slots=True)
class VariableFlowNode:
    node_id: str
    symbol_id: str
    name: str
    scope: str
    kind: str
    source_node: ASTNode | None = None
    x: float = 0.0
    y: float = 0.0
    width: float = 180.0
    height: float = 64.0
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class VariableFlowEdge:
    edge_id: str
    source_id: str
    target_id: str
    edge_type: str = "data"
    label: str = ""
    source_node: ASTNode | None = None
    target_node: ASTNode | None = None


@dataclass(slots=True)
class VariableFlowGraph:
    source_file: Path | None
    language: str
    variable_name: str
    scope: str
    symbol_id: str
    nodes: list[VariableFlowNode] = field(default_factory=list)
    edges: list[VariableFlowEdge] = field(default_factory=list)


__all__ = ["VariableFlowEdge", "VariableFlowGraph", "VariableFlowNode"]
