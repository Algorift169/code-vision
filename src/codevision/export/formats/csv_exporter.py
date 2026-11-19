from __future__ import annotations

import csv
from pathlib import Path

from ..report_builder import ReportModel
from .base_exporter import BaseExporter, ExportMetadata


class CSVExporter(BaseExporter):
    format_name = "csv"
    extension = ".csv"

    def export(self, report: ReportModel, output_path: Path, assets_dir: Path | None = None) -> ExportMetadata:
        path = self.prepare_output(output_path)
        self.validate(report, path)
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["section", "table", "record", "column", "value"])
            record_index = 0
            for section in report.sections:
                for table in section.tables:
                    title = str(table.get("title", "Table"))
                    columns = table.get("columns", [])
                    for row_index, row in enumerate(table.get("rows", []), start=1):
                        record_index += 1
                        for column, value in zip(columns, row):
                            writer.writerow([section.section_id, title, row_index, column, value])
        return ExportMetadata("CSV", path, path.stat().st_size, [section.section_id for section in report.sections])
