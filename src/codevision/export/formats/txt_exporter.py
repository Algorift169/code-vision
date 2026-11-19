from __future__ import annotations

from pathlib import Path

from ..report_builder import ReportModel
from .base_exporter import BaseExporter, ExportMetadata


class TXTExporter(BaseExporter):
    format_name = "txt"
    extension = ".txt"

    def export(self, report: ReportModel, output_path: Path, assets_dir: Path | None = None) -> ExportMetadata:
        path = self.prepare_output(output_path)
        self.validate(report, path)
        meta = report.metadata
        lines = ["=" * 72, meta.title, "=" * 72, f"Project: {meta.project_name}", f"Project root: {meta.project_root or 'Not specified'}", f"Language: {meta.primary_language or 'Unknown'}", f"Generated: {meta.generated_at}", f"Analysis status: {meta.analysis_status}", ""]
        for section in report.sections:
            lines.extend(["-" * 72, section.title, f"Status: {section.status}"])
            if section.description:
                lines.extend(["", section.description])
            for table in section.tables:
                lines.extend(["", table.get("title", "Table"), " | ".join(str(column) for column in table.get("columns", []))])
                lines.extend(" | ".join(str(value) for value in row) for row in table.get("rows", []))
            for block in section.code_blocks:
                lines.extend(["", block.get("title", "Code"), str(block.get("code") or "")])
            for graph in section.graph_references:
                lines.append(f"Graph: {graph.get('title', 'Graph')} - {graph.get('asset') or 'No asset generated'}")
            if not section.tables and not section.code_blocks and not section.graph_references:
                lines.extend(["", str(section.content)])
            lines.append("")
        path.write_text("\n".join(lines), encoding="utf-8")
        return ExportMetadata("TXT", path, path.stat().st_size, [section.section_id for section in report.sections])
