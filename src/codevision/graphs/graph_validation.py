from __future__ import annotations

from .flowchart_ir import FlowchartGraph, GraphValidationResult


class GraphValidator:
    def validate(self, graph: FlowchartGraph) -> GraphValidationResult:
        return graph.validate()


__all__ = ["GraphValidator"]
