from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Callable, Iterable

from .export_context import ExportContext
from .export_errors import ExportError
from .formats.base_exporter import ExportMetadata
from .formats.csv_exporter import CSVExporter
from .formats.docx_exporter import DOCXExporter
from .formats.html_exporter import HTMLExporter
from .formats.json_exporter import JSONExporter
from .formats.markdown_exporter import MarkdownExporter
from .formats.pdf_exporter import PDFExporter
from .formats.txt_exporter import TXTExporter
from .formats.xlsx_exporter import XLSXExporter
from .formats.zip_exporter import ZIPExporter
from .report_builder import ReportBuilder, ReportModel
from .report_manifest import ReportManifest


@dataclass(slots=True)
class ExportResult:
    success: bool
    output_directory: Path
    generated: list[ExportMetadata] = field(default_factory=list)
    failures: list[dict[str, str]] = field(default_factory=list)
    manifest: ReportManifest | None = None

    @property
    def paths(self) -> list[Path]:
        return [item.path for item in self.generated]


class ExportManager:
    """Coordinate report generation, format exporters, and ZIP packaging."""

    def __init__(self) -> None:
        self._lock = Lock()

    def export(
        self,
        context: ExportContext,
        output_directory: Path,
        formats: Iterable[str],
        *,
        output_name: str = "codevision-report",
        overwrite: bool = False,
        progress: Callable[[str], None] | None = None,
    ) -> ExportResult:
        output_directory = Path(output_directory)
        output_directory.mkdir(parents=True, exist_ok=True)
        report = ReportBuilder().build(context)
        selected = tuple(dict.fromkeys(format.lower().lstrip(".") for format in formats))
        exporters = {
            "html": (HTMLExporter(), "report.html"),
            "json": (JSONExporter(), "analysis.json"),
            "pdf": (PDFExporter(), "report.pdf"),
            "docx": (DOCXExporter(), "report.docx"),
            "md": (MarkdownExporter(), "report.md"),
            "markdown": (MarkdownExporter(), "report.md"),
            "csv": (CSVExporter(), "metrics.csv"),
            "xlsx": (XLSXExporter(), "analysis.xlsx"),
            "txt": (TXTExporter(), "report.txt"),
        }
        generated: list[ExportMetadata] = []
        failures: list[dict[str, str]] = []
        arc_files: dict[str, Path] = {}

        for format_name in selected:
            if format_name == "zip":
                continue
            if format_name not in exporters:
                failures.append({"format": format_name, "error": f"Unsupported export format: {format_name}"})
                continue
            exporter, default_name = exporters[format_name]
            filename = default_name if output_name == "codevision-report" else f"{output_name}{exporter.extension}"
            path = output_directory / filename
            if path.exists() and not overwrite:
                failures.append({"format": format_name, "error": f"Output already exists: {path}"})
                continue
            if progress:
                progress(format_name.upper())
            try:
                metadata = exporter.export(report, path)
                generated.append(metadata)
                arc_files[default_name] = metadata.path
            except (ExportError, OSError, RuntimeError, ValueError, TypeError) as error:
                failures.append({"format": format_name, "error": str(error)})

        if "zip" in selected:
            manifest = ReportManifest(
                project={"name": report.metadata.project_name, "root": report.metadata.project_root, "language": report.metadata.primary_language},
                generated_formats=[item.format for item in generated],
                included_sections=[section.section_id for section in report.sections],
                graph_assets=[str(path) for path in context.graph_assets.values()],
                files=[{"path": str(item.path), "size_bytes": item.size_bytes, "format": item.format} for item in generated],
                completeness_status="complete" if not failures else "partial",
                errors=failures,
            )
            zip_path = output_directory / (f"{output_name}.zip" if output_name != "codevision-report" else "codevision-export.zip")
            if zip_path.exists() and not overwrite:
                failures.append({"format": "zip", "error": f"Output already exists: {zip_path}"})
            else:
                if progress:
                    progress("ZIP")
                try:
                    zip_metadata = ZIPExporter().export(report, zip_path, assets_dir=None, files=arc_files, manifest=manifest)
                    generated.append(zip_metadata)
                except (ExportError, OSError, RuntimeError, ValueError, TypeError) as error:
                    failures.append({"format": "zip", "error": str(error)})
        else:
            manifest = ReportManifest(
                project={"name": report.metadata.project_name, "root": report.metadata.project_root, "language": report.metadata.primary_language},
                generated_formats=[item.format for item in generated],
                included_sections=[section.section_id for section in report.sections],
                files=[{"path": str(item.path), "size_bytes": item.size_bytes, "format": item.format} for item in generated],
                completeness_status="complete" if not failures else "partial",
                errors=failures,
            )
        return ExportResult(success=not failures, output_directory=output_directory, generated=generated, failures=failures, manifest=manifest)
