from __future__ import annotations

from .flowchart_ir import FlowchartGraph


class ControlFlowGraph:
    """Compatibility wrapper for flowchart graphs."""

    @staticmethod
    def from_graph(graph: FlowchartGraph) -> FlowchartGraph:
        return graph


__all__ = ["ControlFlowGraph"]
