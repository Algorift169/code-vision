from __future__ import annotations

from typing import Any


class GraphCollector:
    """Collect existing graph objects and references from an export context."""

    def collect(self, analysis: dict[str, Any]) -> dict[str, Any]:
        names = ("ast", "call_graph", "dependencies", "flowcharts", "variable_flow_graph")
        return {name: analysis[name] for name in names if analysis.get(name) is not None}
