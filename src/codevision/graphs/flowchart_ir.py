from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class FlowchartNodeKind(str, Enum):
    START = "start"
    END = "end"
    PROCESS = "process"
    INPUT = "input"
    OUTPUT = "output"
    DECISION = "decision"
    LOOP = "loop"
    FUNCTION = "function"
    RETURN = "return"
    BREAK = "break"
    CONTINUE = "continue"
    EXCEPTION = "exception"
    MERGE = "merge"
    CONNECTOR = "connector"


@dataclass(slots=True)
class FlowchartNode:
    node_id: str
    kind: FlowchartNodeKind
    label: str
    source_text: str = ""
    source_file: Path | None = None
    line: int | None = None
    column: int | None = None
    x: float = 0.0
    y: float = 0.0
    width: float = 160.0
    height: float = 60.0
    incoming: list[str] = field(default_factory=list)
    outgoing: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class FlowchartEdge:
    edge_id: str
    source_id: str
    target_id: str
    edge_type: str = "normal"
    branch_label: str | None = None
    source_file: Path | None = None
    line: int | None = None
    column: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class GraphValidationResult:
    valid: bool
    issues: list[str] = field(default_factory=list)


@dataclass(slots=True)
class FlowchartGraph:
    graph_id: str
    source_file: Path | None
    language: str
    function_name: str | None = None
    nodes: list[FlowchartNode] = field(default_factory=list)
    edges: list[FlowchartEdge] = field(default_factory=list)
    entry: str | None = None
    exit_nodes: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> GraphValidationResult:
        issues: list[str] = []
        seen_ids: set[str] = set()
        for node in self.nodes:
            if node.node_id in seen_ids:
                issues.append(f"duplicate node id: {node.node_id}")
            seen_ids.add(node.node_id)
        for edge in self.edges:
            if isinstance(edge, str):
                issues.append(f"edge record is not a FlowchartEdge: {edge}")
                continue
            source_id = getattr(edge, "source_id", None)
            target_id = getattr(edge, "target_id", None)
            if source_id not in seen_ids:
                issues.append(f"edge source missing: {source_id}")
            if target_id not in seen_ids:
                issues.append(f"edge target missing: {target_id}")
        if self.entry is None:
            issues.append("graph entry node is missing")
        elif self.entry not in seen_ids:
            issues.append(f"entry node is missing: {self.entry}")
        if not self.exit_nodes:
            issues.append("graph has no exit nodes")
        for exit_id in self.exit_nodes:
            if exit_id not in seen_ids:
                issues.append(f"exit node missing: {exit_id}")
        return GraphValidationResult(valid=not issues, issues=issues)


__all__ = [
    "FlowchartEdge",
    "FlowchartGraph",
    "FlowchartNode",
    "FlowchartNodeKind",
    "GraphValidationResult",
]
