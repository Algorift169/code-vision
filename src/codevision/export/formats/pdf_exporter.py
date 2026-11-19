from __future__ import annotations

from pathlib import Path

from ..export_errors import ExportError
from ..report_builder import ReportModel
from .base_exporter import BaseExporter, ExportMetadata


class PDFExporter(BaseExporter):
    format_name = "pdf"
    extension = ".pdf"

    def export(self, report: ReportModel, output_path: Path, assets_dir: Path | None = None) -> ExportMetadata:
        path = self.prepare_output(output_path)
        self.validate(report, path)
        try:
            from reportlab.lib import colors
            from reportlab.lib.enums import TA_CENTER
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import mm
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, KeepTogether
        except ImportError as error:
            raise ExportError("PDF export requires the 'reportlab' dependency") from error

        def header_footer(canvas, document):
            canvas.saveState()
            canvas.setFont("Helvetica", 8)
            canvas.drawString(18 * mm, 10 * mm, report.metadata.project_name)
            canvas.drawRightString(192 * mm, 10 * mm, f"Page {canvas.getPageNumber()}")
            canvas.restoreState()

        document = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm, topMargin=18 * mm, bottomMargin=15 * mm)
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle("CoverTitle", parent=styles["Title"], alignment=TA_CENTER, fontSize=24, leading=29, spaceAfter=18)
        story = [Paragraph(report.metadata.title, title_style), Spacer(1, 18 * mm), Paragraph(f"Project: {report.metadata.project_name}", styles["Heading2"]), Paragraph(f"Root: {report.metadata.project_root or 'Not specified'}", styles["BodyText"]), Paragraph(f"Language: {report.metadata.primary_language or 'Unknown'}", styles["BodyText"]), Paragraph(f"Generated: {report.metadata.generated_at}", styles["BodyText"]), PageBreak(), Paragraph("Table of Contents", styles["Heading1"])]
        for index, section in enumerate(report.sections, start=1):
            story.append(Paragraph(f"{index}. {section.title}", styles["BodyText"]))
        story.append(PageBreak())

        for section in report.sections:
            story.append(KeepTogether([Paragraph(section.title, styles["Heading1"]), Paragraph(f"Status: {section.status}", styles["Italic"])]))
            if section.description:
                story.append(Paragraph(section.description, styles["BodyText"]))
            for table in section.tables:
                story.append(Paragraph(str(table.get("title", "Table")), styles["Heading2"]))
                columns = [str(column) for column in table.get("columns", [])]
                rows = table.get("rows", [])
                data = [columns] + [[str(value) for value in row] for row in rows]
                if data:
                    pdf_table = Table(data, repeatRows=1, hAlign="LEFT")
                    pdf_table.setStyle(TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dde7f2")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#7f8c8d")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("FONTSIZE", (0, 0), (-1, -1), 7),
                        ("LEADING", (0, 0), (-1, -1), 9),
                    ]))
                    story.append(pdf_table)
            for block in section.code_blocks:
                story.append(Paragraph(str(block.get("title", "Code")), styles["Heading2"]))
                code = str(block.get("code") or "")
                for start in range(0, len(code), 2000):
                    story.append(Paragraph(code[start:start + 2000].replace("&", "&amp;").replace("<", "&lt;").replace("\n", "<br/>"), styles["Code"] if "Code" in styles else styles["BodyText"]))
            for graph in section.graph_references:
                story.append(Paragraph(f"Graph: {graph.get('title', 'Graph')} - {graph.get('asset') or 'No asset generated'}", styles["BodyText"]))
            if not section.tables and not section.code_blocks and not section.graph_references:
                story.append(Paragraph(str(section.content).replace("\n", "<br/>"), styles["BodyText"]))
            story.append(Spacer(1, 5 * mm))

        document.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
        return ExportMetadata("PDF", path, path.stat().st_size, [section.section_id for section in report.sections])
