from pathlib import Path
from tempfile import TemporaryDirectory

from codevision.export.analysis_collector import AnalysisCollector
from codevision.export.formats.html_exporter import HTMLExporter
from codevision.export.formats.json_exporter import JSONExporter
from codevision.export.formats.markdown_exporter import MarkdownExporter
from codevision.export.formats.txt_exporter import TXTExporter
from codevision.export.report_builder import ReportBuilder


class ASTViewStub:
    result = None


class PanelStub:
    source_text = "def hello():\n    return 1\n"
    source_file_path = Path("example.py")
    _project_root = None
    _section_placeholders = {"AST": ASTViewStub()}


def test_export_core_formats_from_panel_state(tmp_path):
    context = AnalysisCollector().collect(PanelStub())
    report = ReportBuilder().build(context)
    assert report.sections

    for exporter, name in (
        (JSONExporter(), "report.json"),
        (HTMLExporter(), "report.html"),
        (MarkdownExporter(), "report.md"),
        (TXTExporter(), "report.txt"),
    ):
        metadata = exporter.export(report, tmp_path / name)
        assert metadata.path.is_file()
        assert metadata.path.stat().st_size > 0

    json_text = (tmp_path / "report.json").read_text(encoding="utf-8")
    assert '"schema_version": "1.0"' in json_text
