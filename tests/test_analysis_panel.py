import gi
import pytest

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from codevision.ui.analysis_panel import SECTIONS, AnalysisPanel
from codevision.ui.ast_view import ASTView
from codevision.ui.graphs import CallGraphView, FlowchartView


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
    if section == "AST":
        assert isinstance(placeholder, ASTView)
    elif section == "Flowchart":
        assert isinstance(placeholder, FlowchartView)
        assert isinstance(placeholder.canvas, Gtk.DrawingArea)
    elif section == "Call Graph":
        assert isinstance(placeholder, CallGraphView)
        assert isinstance(placeholder.canvas, Gtk.DrawingArea)
    else:
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


def test_analysis_panel_updates_flowchart_view_when_source_changes(tmp_path) -> None:
    panel = AnalysisPanel()
    flowchart = panel._section_placeholders["Flowchart"]
    assert isinstance(flowchart, FlowchartView)

    source = "int main() { return 0; }"
    panel.set_source(source, tmp_path / "main.c", "c")

    assert flowchart.graph is not None
    assert flowchart.graph.language == "c"
    assert flowchart.graph.entry is not None


def test_flowchart_function_selector_switches_graphs(tmp_path) -> None:
    panel = AnalysisPanel()
    flowchart = panel._section_placeholders["Flowchart"]
    source = "int first() { return 1; } int second() { return 2; }"

    panel.set_source(source, tmp_path / "functions.c", "c")
    flowchart.function_selector.set_selected(1)

    assert flowchart.graph.function_name == "second"


def test_analysis_panel_updates_call_graph_view_when_source_changes(tmp_path) -> None:
    panel = AnalysisPanel()
    call_graph = panel._section_placeholders["Call Graph"]
    source = "int leaf() { return 1; } int root() { return leaf(); }"

    panel.set_source(source, tmp_path / "calls.c", "c")

    assert call_graph.graph is not None
    assert len(call_graph.graph.nodes) == 2
    assert len(call_graph.graph.edges) == 1


def test_flowchart_node_click_navigates_to_ast_source(tmp_path) -> None:
    navigated = []
    flowchart = FlowchartView(on_source_navigate=navigated.append)
    source = "int main() { int value = 1; return value; }"
    flowchart.set_source(source, tmp_path / "main.c", "c")
    node = next(node for node in flowchart.graph.nodes if node.kind.value == "process")
    scale, origin_x = flowchart._graph_transform(
        flowchart.graph, max(1, flowchart.canvas.get_width())
    )

    flowchart._on_canvas_pressed(
        None,
        1,
        origin_x + (node.x + node.width / 2) * scale,
        16 + (node.y + node.height / 2) * scale,
    )

    assert len(navigated) == 1
    assert navigated[0].node_type == "declaration"
    assert flowchart._selected_node_id == node.node_id


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
    assert window.center_stack.get_size_request()[0] == 180
    assert window.analysis_panel.get_size_request()[0] == 0

    window.toggle_analysis_panel()
    assert not window.analysis_panel_visible()
    assert window.right_pane.get_end_child() is window._analysis_placeholder

    window.right_pane.set_position(500)
    window.show_analysis_panel()
    assert window.analysis_panel_visible()
    assert window.right_pane.get_end_child() is window.analysis_panel
    assert window.right_pane.get_position() == 180
