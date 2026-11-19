from __future__ import annotations

from pathlib import Path

from ..export_errors import ExportError
from ..report_builder import ReportModel
from .base_exporter import BaseExporter, ExportMetadata


class XLSXExporter(BaseExporter):
    format_name = "xlsx"
    extension = ".xlsx"

    def export(self, report: ReportModel, output_path: Path, assets_dir: Path | None = None) -> ExportMetadata:
        path = self.prepare_output(output_path)
        self.validate(report, path)
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font
            from openpyxl.utils import get_column_letter
        except ImportError as error:
            raise ExportError("XLSX export requires the optional 'openpyxl' dependency") from error

        workbook = Workbook()
        overview = workbook.active
        overview.title = "Overview"
        overview.append(["Project", "Value"])
        overview.append(["Project name", report.metadata.project_name])
        overview.append(["Project root", report.metadata.project_root or ""])
        overview.append(["Language", report.metadata.primary_language or ""])
        overview.append(["Generated", report.metadata.generated_at])

        used_names: set[str] = set()
        for section_index, section in enumerate(report.sections):
            sheet_name = section.title[:31]
            candidate = sheet_name
            suffix = 2
            while candidate in used_names:
                candidate = f"{sheet_name[:28]}_{suffix}"
                suffix += 1
            used_names.add(candidate)
            sheet = workbook.create_sheet(candidate)
            sheet.append(["Status", section.status])
            sheet.append(["Description", section.description])
            sheet.append([])
            for table_index, table in enumerate(section.tables):
                if table_index:
                    sheet.append([])
                sheet.append([str(table.get("title", "Table") )])
                columns = table.get("columns", [])
                sheet.append(list(columns))
                for row in table.get("rows", []):
                    sheet.append(list(row))
            for row in sheet.iter_rows():
                for cell in row:
                    if cell.row <= 3:
                        cell.font = Font(bold=True)
            sheet.freeze_panes = "A4"
            sheet.auto_filter.ref = sheet.dimensions
            for column_index, column_cells in enumerate(sheet.columns, start=1):
                length = min(60, max(len(str(cell.value or "")) for cell in column_cells))
                sheet.column_dimensions[get_column_letter(column_index)].width = max(12, length + 2)

        for sheet in workbook.worksheets:
            for cell in sheet[1]:
                cell.font = Font(bold=True)
        workbook.save(path)
        return ExportMetadata("XLSX", path, path.stat().st_size, [section.section_id for section in report.sections])
