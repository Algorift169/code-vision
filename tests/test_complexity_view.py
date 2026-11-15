from pathlib import Path

from codevision.ui.analysis_panel import AnalysisPanel


def test_complexity_header_zoom_buttons_change_only_local_zoom() -> None:
    panel = AnalysisPanel()
    complexity_view = panel._section_placeholders["Complexity"]

    complexity_view.zoom_out_button.emit("clicked")
    assert complexity_view._zoom_level == -1
    complexity_view.zoom_in_button.emit("clicked")

    assert complexity_view._zoom_level == 0
    assert complexity_view._zoom_provider is not None


def test_analysis_panel_complexity_section_populates_metrics(tmp_path: Path) -> None:
    panel = AnalysisPanel()
    complexity_view = panel._section_placeholders["Complexity"]
    source = """
def compute(items):
    total = 0
    for item in items:
        total += item
    return total
"""

    panel.set_source(source, tmp_path / "sample.py", "python")

    assert complexity_view._report is not None
    assert complexity_view._report.functions
    assert complexity_view._report.functions[0].name == "compute"
    assert len(list(complexity_view.summary)) > 0
