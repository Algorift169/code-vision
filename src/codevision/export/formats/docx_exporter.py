from __future__ import annotations

from pathlib import Path

from ..export_errors import ExportError
from ..report_builder import ReportModel
from .base_exporter import BaseExporter, ExportMetadata


class DOCXExporter(BaseExporter):
    format_name = "docx"
    extension = ".docx"

    def export(self, report: ReportModel, output_path: Path, assets_dir: Path | None = None) -> ExportMetadata:
        path = self.prepare_output(output_path)
        self.validate(report, path)
        try:
            from docx import Document
            from docx.enum.style import WD_STYLE_TYPE
            from docx.enum.text import WD_ALIGN_PARAGRAPH
            from docx.shared import Inches
        except ImportError as error:
            raise ExportError("DOCX export requires the optional 'python-docx' dependency") from error

        document = Document()
        section = document.sections[0]
        section.top_margin = Inches(0.75)
        section.bottom_margin = Inches(0.75)
        section.left_margin = Inches(0.75)
        section.right_margin = Inches(0.75)

        title = document.add_paragraph()
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        title.style = document.styles["Title"]
        title.add_run(report.metadata.title)
        document.add_paragraph(f"Project: {report.metadata.project_name}").alignment = WD_ALIGN_PARAGRAPH.CENTER
        document.add_paragraph(f"Root: {report.metadata.project_root or 'Not specified'}").alignment = WD_ALIGN_PARAGRAPH.CENTER
        document.add_paragraph(f"Language: {report.metadata.primary_language or 'Unknown'}").alignment = WD_ALIGN_PARAGRAPH.CENTER
        document.add_paragraph(f"Generated: {report.metadata.generated_at}").alignment = WD_ALIGN_PARAGRAPH.CENTER
        document.add_page_break()

        document.add_heading("Table of Contents", level=1)
        paragraph = document.add_paragraph()
        run = paragraph.add_run()
        fld_char = run._r.add_sdt() if hasattr(run._r, "add_sdt") else None
        document.add_page_break()

        for report_section in report.sections:
            document.add_heading(report_section.title, level=1)
            document.add_paragraph(f"Status: {report_section.status}", style="Intense Quote")
            if report_section.description:
                document.add_paragraph(report_section.description)
            for table in report_section.tables:
                document.add_heading(str(table.get("title", "Table")), level=2)
                columns = table.get("columns", [])
                rows = table.get("rows", [])
                doc_table = document.add_table(rows=1, cols=len(columns))
                doc_table.style = "Table Grid"
                try:
                    from docx.oxml import OxmlElement
                    from docx.oxml.ns import qn
                    header_properties = OxmlElement("w:tblHeader")
                    header_properties.set(qn("w:val"), "true")
                    doc_table.rows[0]._tr.get_or_add_trPr().append(header_properties)
                except ImportError:
                    pass
                for index, column in enumerate(columns):
                    doc_table.rows[0].cells[index].text = str(column)
                for row in rows:
                    cells = doc_table.add_row().cells
                    for index, value in enumerate(row):
                        if index < len(cells):
                            cells[index].text = str(value)
            for block in report_section.code_blocks:
                document.add_heading(str(block.get("title", "Code")), level=2)
                document.add_paragraph(str(block.get("code") or ""), style="No Spacing")
            for graph in report_section.graph_references:
                document.add_paragraph(f"Graph: {graph.get('title', 'Graph')} - {graph.get('asset') or 'No asset generated'}")
            if not report_section.tables and not report_section.code_blocks and not report_section.graph_references:
                document.add_paragraph(str(report_section.content))

        header = document.sections[0].header
        header.paragraphs[0].text = f"CodeVision - {report.metadata.project_name}"
        footer = document.sections[0].footer
        footer.paragraphs[0].text = "CodeVision report"
        document.save(path)
        return ExportMetadata("DOCX", path, path.stat().st_size, [section.section_id for section in report.sections])
