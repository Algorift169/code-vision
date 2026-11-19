from __future__ import annotations

import json
from pathlib import Path

from ..data_serializer import serialize_value
from ..export_errors import ExportValidationError
from ..report_builder import ReportModel
from .base_exporter import BaseExporter, ExportMetadata


class JSONExporter(BaseExporter):
    format_name = "json"
    extension = ".json"

    def export(self, report: ReportModel, output_path: Path, assets_dir: Path | None = None) -> ExportMetadata:
        path = self.prepare_output(output_path)
        self.validate(report, path)
        payload = {
            "schema_version": report.metadata.schema_version,
            "metadata": serialize_value(report.metadata, "metadata"),
            "sections": serialize_value(report.sections, "sections"),
        }
        try:
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except (OSError, TypeError, ValueError) as error:
            raise ExportValidationError(f"Could not write JSON report: {error}") from error
        if not path.is_file() or path.stat().st_size == 0:
            raise ExportValidationError("JSON exporter did not produce a readable report")
        return ExportMetadata("JSON", path, path.stat().st_size, [section.section_id for section in report.sections])
