from __future__ import annotations

from pathlib import Path

from ..report_builder import ReportModel
from .base_exporter import BaseExporter, ExportMetadata


class MarkdownExporter(BaseExporter):
    format_name = "markdown"
    extension = ".md"

    def export(self, report: ReportModel, output_path: Path, assets_dir: Path | None = None) -> ExportMetadata:
        path = self.prepare_output(output_path)
        self.validate(report, path)
        meta = report.metadata
        lines = [f"# {meta.title}", "", "## Project Information", "", f"- Project: {meta.project_name}", f"- Project root: `{meta.project_root or 'Not specified'}`", f"- Language: {meta.primary_language or 'Unknown'}", f"- Generated: {meta.generated_at}", f"- Analysis status: {meta.analysis_status}", "", "## Table of Contents", ""]
        lines.extend(f"- [{section.title}](#{section.section_id})" for section in report.sections)
        for section in report.sections:
            lines.extend(["", f"## {section.title}", "", f"**Status:** `{section.status}`", ""])
            if section.description:
                lines.extend([section.description, ""])
            for table in section.tables:
                columns = table.get("columns", [])
                rows = table.get("rows", [])
                lines.extend([f"### {table.get('title', 'Table')}", "", "| " + " | ".join(str(column).replace("|", "\\|") for column in columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"])
                lines.extend("| " + " | ".join(str(value).replace("|", "\\|").replace("\n", " ") for value in row) + " |" for row in rows)
                lines.append("")
            for block in section.code_blocks:
                lines.extend([f"### {block.get('title', 'Code')}", "", f"```{block.get('language') or ''}", str(block.get("code") or ""), "```", ""])
            for graph in section.graph_references:
                asset = graph.get("asset")
                lines.extend([f"- Graph: **{graph.get('title', 'Graph')}**" + (f" ({asset})" if asset else " (no asset generated)")])
            if not section.tables and not section.code_blocks and not section.graph_references:
                lines.extend(["```json", str(section.content).replace("```", "`​``"), "```", ""])
        path.write_text("\n".join(lines), encoding="utf-8")
        return ExportMetadata("Markdown", path, path.stat().st_size, [section.section_id for section in report.sections])
