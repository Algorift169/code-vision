import gi
import pytest

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from codevision.ui.analysis_panel import SECTIONS, AnalysisPanel


def test_analysis_panel_has_all_sections_in_order() -> None:
    panel = AnalysisPanel()

    assert panel.sections == (
        "Overview",
        "AST",
        "Flowchart",
        "Call Graph",
        "Var Flow",
        "Complexity",
        "Warnings",
        "Export",
    )
    assert tuple(panel.section_buttons) == panel.sections
    assert len(panel.section_buttons) == 8
    assert panel.get_size_request() == (0, -1)


@pytest.mark.parametrize("section", SECTIONS)
def test_analysis_section_selects_its_placeholder(section: str) -> None:
    panel = AnalysisPanel()
    button = panel.section_buttons[section]

    button.emit("clicked")

    placeholder = panel.views.get_visible_child()
    assert panel.current_section == section
    assert button.get_active()
    assert placeholder is panel._section_placeholders[section]
    assert placeholder.get_first_child().get_text() == section

    for other_section, other_button in panel.section_buttons.items():
        assert other_button.get_active() is (other_section == section)


def test_analysis_navigation_scrolls_horizontally() -> None:
    panel = AnalysisPanel()
    scroller = panel.get_first_child()

    assert isinstance(scroller, Gtk.ScrolledWindow)
    assert scroller.get_policy() == (
        Gtk.PolicyType.AUTOMATIC,
        Gtk.PolicyType.NEVER,
    )
    assert scroller.get_child().get_child() is panel.navigation


def test_unknown_analysis_section_is_rejected() -> None:
    panel = AnalysisPanel()

    with pytest.raises(ValueError, match="Unknown analysis section"):
        panel.select_section("Parser")


def test_analysis_panel_can_shrink_to_edge_and_be_reopened() -> None:
    from codevision.app.main_window import CodeVisionWindow

    window = CodeVisionWindow(
        Gtk.Application(application_id="com.codevision.test.analysis-panel")
    )

    assert window.right_pane.get_shrink_start_child()
    assert window.right_pane.get_shrink_end_child()
    assert window.center_stack.get_size_request()[0] == 0
    assert window.analysis_panel.get_size_request()[0] == 0

    window.toggle_analysis_panel()
    assert not window.analysis_panel_visible()
    assert window.right_pane.get_end_child() is window._analysis_placeholder

    window.show_analysis_panel()
    assert window.analysis_panel_visible()
    assert window.right_pane.get_end_child() is window.analysis_panel
