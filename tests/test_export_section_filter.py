from pathlib import Path

from codevision.export.export_context import ExportContext
from codevision.export.report_builder import ReportBuilder


def test_ast_menu_export_filters_to_ast_section():
    context = ExportContext(
        project_root=Path("/tmp/example"),
        source="def value():\n    return 1\n",
        source_file=Path("/tmp/example/example.py"),
        language="python",
        selected_section="AST",
        analysis={"ast": None},
    )

    report = ReportBuilder().build(context)

    assert [section.section_id for section in report.sections] == ["ast"]


def test_complete_menu_export_keeps_all_report_sections():
    context = ExportContext(selected_section=None)

    report = ReportBuilder().build(context)

    assert len(report.sections) >= 12
