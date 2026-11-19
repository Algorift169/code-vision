from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

from .data_serializer import clear_serialization_errors, serialize_value, serialization_errors
from .export_context import ExportContext
from .report_metadata import ReportMetadata
from .report_section import ReportSection


@dataclass(slots=True)
class ReportModel:
    metadata: ReportMetadata
    sections: list[ReportSection] = field(default_factory=list)

    def section_by_id(self, section_id: str) -> ReportSection | None:
        return next((section for section in self.sections if section.section_id == section_id), None)


class ReportBuilder:
    """Build a complete report model while recording unavailable analysis states."""

    def __init__(self) -> None:
        self._registered_sections: dict[str, Callable[[ExportContext], ReportSection]] = {}

    def register_section(self, section_id: str, builder: Callable[[ExportContext], ReportSection]) -> None:
        self._registered_sections[section_id] = builder

    def build(self, context: ExportContext) -> ReportModel:
        clear_serialization_errors()
        metadata = ReportMetadata.for_project(context.project_root, context.language)
        metadata.generated_at = datetime.now(timezone.utc).isoformat()
        sections = [
            self._project_section(context),
            self._ast_section(context),
            self._complexity_section(context),
            self._dependency_section(context),
            self._call_graph_section(context),
            self._control_flow_section(context),
            self._variable_flow_section(context),
            self._diagnostics_section(context),
            self._memory_section(context),
            self._graphical_section(context),
            self._additional_section(context),
            self._summary_section(context),
        ]
        for section_id, builder in self._registered_sections.items():
            section = builder(context)
            if section.section_id != section_id:
                section.section_id = section_id
            sections.append(section)
        metadata.extra["serialization_errors"] = serialization_errors()
        metadata.extra["collected_categories"] = sorted(key for key, value in context.analysis.items() if value is not None)
        if context.selected_section:
            section_aliases = {
                "Overview": {"project-information", "final-summary"},
                "AST": {"ast"},
                "Flowchart": {"control-flow"},
                "Call Graph": {"call-graph"},
                "Var Flow": {"variable-flow"},
                "Complexity": {"complexity"},
                "Dependency": {"dependency"},
                "Space": {"additional"},
            }
            selected_ids = section_aliases.get(context.selected_section)
            if selected_ids:
                sections = [section for section in sections if section.section_id in selected_ids]
        return ReportModel(metadata=metadata, sections=sections)

    @staticmethod
    def _status_for(value: Any) -> tuple[str, str]:
        if value is None:
            return "not-performed", "This analysis category was not available in the current application state."
        if isinstance(value, (list, tuple)) and not value:
            return "no-findings", "Analysis was performed, and no findings were recorded."
        if isinstance(value, dict) and not value:
            return "no-findings", "Analysis was performed, and no findings were recorded."
        return "performed", "Analysis results are available."

    def _project_section(self, context: ExportContext) -> ReportSection:
        files: list[dict[str, Any]] = []
        if context.project_root is not None:
            root = context.project_root
            skip = {".git", "node_modules", "build", "dist", "__pycache__", ".venv", "venv"}
            if root.is_dir():
                for path in sorted(root.rglob("*")):
                    if path.is_file() and not any(part in skip for part in path.parts):
                        files.append({"path": str(path), "extension": path.suffix or "(none)"})
        content = {
            "project_root": str(context.project_root) if context.project_root else None,
            "source_file": str(context.source_file) if context.source_file else None,
            "language": context.language,
            "analyzed_files": len(files),
            "file_list": files,
        }
        status = "performed" if files or context.project_root else "not-performed"
        return ReportSection("project-information", "Project Information", status=status, content=content)

    def _ast_section(self, context: ExportContext) -> ReportSection:
        value = context.analysis.get("ast")
        status, description = self._status_for(value)
        content = serialize_value(value, "analysis.ast") if value is not None else {}
        statistics = context.analysis.get("ast_statistics")
        if statistics is not None:
            content["statistics"] = serialize_value(statistics, "analysis.ast_statistics")
        tables = []
        if value is not None:
            root = getattr(value, "root", None)
            nodes = list(root.walk()) if root is not None else []
            tables.append({"title": "AST Nodes", "columns": ["ID", "Type", "Name", "Line", "Column", "Source"], "rows": [
                [node.node_id, node.node_type, node.display_name, getattr(node.location, "start_line", None), getattr(node.location, "start_column", None), node.source_text]
                for node in nodes
            ]})
        code = [{"title": "Analyzed Source", "language": context.language or "text", "code": context.source}] if context.source is not None else []
        return ReportSection("ast", "AST Analysis", description, status, content, tables, code)

    def _complexity_section(self, context: ExportContext) -> ReportSection:
        value = context.analysis.get("complexity")
        status, description = self._status_for(value)
        content = serialize_value(value, "analysis.complexity") if value is not None else {}
        tables = []
        if value is not None:
            functions = getattr(value, "functions", [])
            tables.append({"title": "Function Complexity", "columns": ["Function", "File", "Line", "Cyclomatic", "Cognitive", "Time", "Space", "Risk", "Explanation"], "rows": [
                [item.name, str(item.file_path) if item.file_path else "", item.line, item.cyclomatic, item.cognitive, item.time_complexity, item.space_complexity, item.risk, item.explanation]
                for item in functions
            ]})
        return ReportSection("complexity", "Complexity Analysis", description, status, content, tables)

    def _dependency_section(self, context: ExportContext) -> ReportSection:
        value = context.analysis.get("dependencies")
        status, description = self._status_for(value)
        content = serialize_value(value, "analysis.dependencies") if value is not None else {}
        tables = []
        if value is not None:
            graph = getattr(value, "graph", None)
            if graph is not None:
                tables.append({"title": "Dependency Edges", "columns": ["Source", "Target", "Kind", "Import", "Line"], "rows": [
                    [edge.source, edge.target, edge.kind, edge.import_name, edge.line] for edge in graph.edges
                ]})
        return ReportSection("dependency", "Dependency Analysis", description, status, content, tables)

    def _call_graph_section(self, context: ExportContext) -> ReportSection:
        value = context.analysis.get("call_graph")
        status, description = self._status_for(value)
        content = serialize_value(value, "analysis.call_graph") if value is not None else {}
        tables = []
        if value is not None:
            tables.append({"title": "Call Graph Edges", "columns": ["Source", "Target", "Call Sites"], "rows": [
                [edge.source_id, edge.target_id, len(edge.call_sites)] for edge in getattr(value, "edges", [])
            ]})
        return ReportSection("call-graph", "Call Graph Analysis", description, status, content, tables)

    def _control_flow_section(self, context: ExportContext) -> ReportSection:
        value = context.analysis.get("flowcharts")
        status, description = self._status_for(value)
        content = serialize_value(value, "analysis.flowcharts") if value is not None else {}
        selected = context.analysis.get("selected_flowchart")
        if selected is not None:
            content["selected_flowchart"] = serialize_value(selected, "analysis.selected_flowchart")
        ast_result = context.analysis.get("flowchart_result")
        if ast_result is not None:
            content["source_ast"] = serialize_value(ast_result, "analysis.flowchart_result")
        tables = []
        if value:
            for graph in value:
                tables.append({"title": f"Control Flow: {graph.function_name or 'Program'}", "columns": ["Node", "Kind", "Label", "Line", "Column"], "rows": [
                    [node.node_id, getattr(node.kind, "value", str(node.kind)), node.label, node.line, node.column] for node in graph.nodes
                ]})
        return ReportSection("control-flow", "Control Flow Analysis", description, status, content, tables)

    def _variable_flow_section(self, context: ExportContext) -> ReportSection:
        value = context.analysis.get("variable_flow")
        status, description = self._status_for(value)
        content = serialize_value(value, "analysis.variable_flow") if value is not None else {}
        selected_fact = context.analysis.get("selected_variable")
        if selected_fact is not None:
            content["selected_variable"] = serialize_value(selected_fact, "analysis.selected_variable")
        graph = context.analysis.get("variable_flow_graph")
        if graph is not None:
            content["selected_graph"] = serialize_value(graph, "analysis.variable_flow_graph")
        tables = []
        if value is not None:
            tables.append({"title": "Variable Flow Facts", "columns": ["Variable", "Scope", "Kind", "Declarations", "Definitions", "Uses"], "rows": [
                [fact.name, fact.scope, fact.kind, 1 if fact.declaration else 0, len(fact.definitions), len(fact.uses)] for fact in getattr(value, "facts", [])
            ]})
        return ReportSection("variable-flow", "Variable Flow Analysis", description, status, content, tables)

    def _diagnostics_section(self, context: ExportContext) -> ReportSection:
        ast = context.analysis.get("ast")
        warnings = []
        errors = []
        if ast is not None:
            errors.extend(getattr(ast, "errors", ()) or ())
        complexity = context.analysis.get("complexity")
        if complexity is not None:
            warnings.extend(getattr(complexity, "warnings", ()) or ())
        status = "performed" if ast is not None or complexity is not None else "not-performed"
        if ast is not None and not errors and not warnings:
            status = "no-findings"
        content = {"warnings": list(warnings), "errors": list(errors)}
        tables = [{"title": "Diagnostics", "columns": ["Severity", "Message", "Source"], "rows": [
            *[["error", message, str(context.source_file) if context.source_file else ""] for message in errors],
            *[["warning", message, str(context.source_file) if context.source_file else ""] for message in warnings],
        ]}]
        return ReportSection("diagnostics", "Diagnostics and Warnings", "Diagnostics from available AST and complexity results.", status, content, tables)

    def _memory_section(self, context: ExportContext) -> ReportSection:
        value = context.analysis.get("memory")
        status, description = self._status_for(value)
        content = serialize_value(value, "analysis.memory") if value is not None else {}
        return ReportSection("memory", "Memory Analysis", description, status, content)

    def _graphical_section(self, context: ExportContext) -> ReportSection:
        refs = []
        for name in ("ast", "call_graph", "dependencies", "flowcharts", "variable_flow_graph"):
            if context.analysis.get(name) is not None:
                refs.append({"id": name, "title": name.replace("_", " ").title(), "asset": context.graph_assets.get(name)})
        status = "performed" if refs else "not-performed"
        return ReportSection("graphical", "Graphical Analysis", "Available graph structures and assets.", status, {}, graph_references=refs)

    def _additional_section(self, context: ExportContext) -> ReportSection:
        known = {"ast", "complexity", "dependencies", "call_graph", "flowcharts", "variable_flow", "variable_flow_graph", "memory"}
        additional = {key: serialize_value(value, f"analysis.{key}") for key, value in context.analysis.items() if key not in known and value is not None}
        status = "performed" if additional else "not-performed"
        return ReportSection("additional", "Additional Analysis", "Analysis categories discovered in the current export context.", status, additional)

    def _summary_section(self, context: ExportContext) -> ReportSection:
        ast = context.analysis.get("ast")
        complexity = context.analysis.get("complexity")
        dependencies = context.analysis.get("dependencies")
        node_count = getattr(ast, "node_count", 0) if ast is not None else 0
        function_count = len(getattr(complexity, "functions", [])) if complexity is not None else 0
        warning_count = len(getattr(complexity, "warnings", [])) if complexity is not None else 0
        error_count = len(getattr(ast, "errors", ()) or ()) if ast is not None else 0
        cycle_count = getattr(dependencies, "summary", {}).get("cycle_count", 0) if dependencies is not None else 0
        content = {
            "ast_node_count": node_count,
            "function_count": function_count,
            "warning_count": warning_count,
            "error_count": error_count,
            "dependency_cycle_count": cycle_count,
        }
        return ReportSection("final-summary", "Final Summary", "Overall findings and report metadata.", "performed", content)
