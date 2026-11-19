from __future__ import annotations

from pathlib import Path
from typing import Any

from .export_context import ExportContext


class AnalysisCollector:
    """Collect existing analysis results without rerunning project-wide analysis."""

    def collect(self, analysis_panel: Any, project_root: Path | None = None) -> ExportContext:
        root = project_root or getattr(analysis_panel, "_project_root", None)
        source = getattr(analysis_panel, "source_text", None)
        source_file = getattr(analysis_panel, "source_file_path", None)
        placeholders = getattr(analysis_panel, "_section_placeholders", {})

        analysis: dict[str, Any] = {}
        ast_view = placeholders.get("AST")
        if ast_view is not None:
            analysis["ast"] = getattr(ast_view, "result", None)
            analysis["ast_statistics"] = getattr(ast_view, "_statistics", None)

        complexity_view = placeholders.get("Complexity")
        if complexity_view is not None:
            report = getattr(complexity_view, "_report", None)
            analysis["complexity"] = report

        dependency_view = placeholders.get("Dependency")
        if dependency_view is not None:
            analysis["dependencies"] = getattr(dependency_view, "_analysis", None)

        flowchart_view = placeholders.get("Flowchart")
        if flowchart_view is not None:
            analysis["flowcharts"] = list(getattr(flowchart_view, "_graphs", []) or [])
            analysis["flowchart_result"] = getattr(flowchart_view, "_result", None)
            analysis["selected_flowchart"] = getattr(flowchart_view, "graph", None)

        call_graph_view = placeholders.get("Call Graph")
        if call_graph_view is not None:
            analysis["call_graph"] = getattr(call_graph_view, "graph", None)

        variable_flow_view = placeholders.get("Var Flow")
        if variable_flow_view is not None:
            analysis["variable_flow"] = getattr(variable_flow_view, "_analysis", None)
            analysis["variable_flow_graph"] = getattr(variable_flow_view, "_graph", None)
            analysis["selected_variable"] = getattr(variable_flow_view, "_selected_fact", None)

        language = None
        ast_result = analysis.get("ast")
        if ast_result is not None:
            language = getattr(ast_result, "language", None)
        for key in ("complexity", "dependencies", "call_graph", "variable_flow"):
            value = analysis.get(key)
            if language is None and value is not None:
                language = getattr(value, "language", None)

        return ExportContext(
            project_root=Path(root) if root is not None else None,
            source=source,
            source_file=Path(source_file) if source_file is not None else None,
            language=language,
            analysis=analysis,
            metadata={"collector": "AnalysisCollector", "source": "live_analysis_state"},
        )
