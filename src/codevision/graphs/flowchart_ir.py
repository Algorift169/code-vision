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
    warnings: list[str] = field(default_factory=list)


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
        warnings: list[str] = []
        seen_ids: set[str] = set()
        node_ids: set[str] = set()
        for node in self.nodes:
            if node.node_id in seen_ids:
                issues.append(f"duplicate node id: {node.node_id}")
            seen_ids.add(node.node_id)
            node_ids.add(node.node_id)
            try:
                FlowchartNodeKind(node.kind)
            except (TypeError, ValueError):
                issues.append(f"invalid node kind: {node.kind}")

        edge_ids: set[str] = set()
        adjacency: dict[str, list[str]] = {node_id: [] for node_id in node_ids}
        for edge in self.edges:
            if not isinstance(edge, FlowchartEdge):
                issues.append(f"edge record is not a FlowchartEdge: {edge!r}")
                continue
            if not edge.edge_id:
                issues.append("edge id is empty")
            elif edge.edge_id in edge_ids:
                issues.append(f"duplicate edge id: {edge.edge_id}")
            edge_ids.add(edge.edge_id)
            if edge.source_id not in node_ids:
                issues.append(f"edge source missing: {edge.source_id}")
            if edge.target_id not in node_ids:
                issues.append(f"edge target missing: {edge.target_id}")
            if edge.source_id in adjacency and edge.target_id in node_ids:
                adjacency[edge.source_id].append(edge.target_id)
            if edge.branch_label and not edge.edge_type in {
                "decision",
                "loop",
                "loop-exit",
                "break",
            }:
                issues.append(
                    f"branch label on non-branch edge: {edge.edge_id}"
                )
        if self.entry is None:
            issues.append("graph entry node is missing")
        elif self.entry not in node_ids:
            issues.append(f"entry node is missing: {self.entry}")
        if not self.exit_nodes:
            issues.append("graph has no exit nodes")
        for exit_id in self.exit_nodes:
            if exit_id not in node_ids:
                issues.append(f"exit node missing: {exit_id}")

        if self.entry in node_ids:
            reachable = {self.entry}
            pending = [self.entry]
            while pending:
                current = pending.pop()
                for target in adjacency[current]:
                    if target not in reachable:
                        reachable.add(target)
                        pending.append(target)
            unreachable = node_ids - reachable
            if unreachable:
                warnings.append(
                    "unreachable nodes: " + ", ".join(sorted(unreachable))
                )
        return GraphValidationResult(
            valid=not issues,
            issues=issues,
            warnings=warnings,
        )


__all__ = [
    "FlowchartEdge",
    "FlowchartGraph",
    "FlowchartNode",
    "FlowchartNodeKind",
    "GraphValidationResult",
]
