import gi
import pytest

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from codevision.ui.analysis_panel import SECTIONS, AnalysisPanel
from codevision.ui.ast_view import ASTView
from codevision.ui.graphs import CallGraphView, DependencyView, FlowchartView
from space.space_view import SpaceView


def test_analysis_panel_has_all_sections_in_order() -> None:
    panel = AnalysisPanel()

    assert panel.sections == (
        "Overview",
        "AST",
        "Flowchart",
        "Call Graph",
        "Var Flow",
        "Complexity",
        "Dependency",
        "Space",
        "Export",
    )
    assert tuple(panel.section_buttons) == panel.sections
    assert len(panel.section_buttons) == 9
    assert panel.get_size_request()[0] > 0


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
    elif section == "Dependency":
        assert isinstance(placeholder, DependencyView)
        assert placeholder.title.get_text() == section
    elif section == "Space":
        assert isinstance(placeholder, SpaceView)
    else:
        assert placeholder.get_first_child().get_text() == section

    for other_section, other_button in panel.section_buttons.items():
        assert other_button.get_active() is (other_section == section)


def test_space_menu_has_all_requested_toolbar_buttons() -> None:
    panel = AnalysisPanel()
    space = panel._section_placeholders["Space"]

    assert isinstance(space, SpaceView)
    assert tuple(space.tool_buttons) == (
        "Pen",
        "Undo",
        "Redo",
        "Eraser",
        "Color",
        "Text Box",
        "Import",
        "Shapes",
        "Zoom In",
        "Zoom Out",
        "Export",
    )
    assert space.canvas.get_name() == "space-canvas"
    assert space.canvas.get_content_width() == 0
    assert space.canvas.get_content_height() == 0
    assert isinstance(space.tool_buttons["Pen"], Gtk.ToggleButton)
    assert isinstance(space.tool_buttons["Color"], Gtk.MenuButton)
    assert not space.tool_buttons["Pen"].get_active()
    assert not space.tool_buttons["Undo"].get_sensitive()
    assert not space.tool_buttons["Redo"].get_sensitive()
    assert space.toolbar.get_orientation() == Gtk.Orientation.HORIZONTAL
    assert space.toolbar_scroller.get_policy() == (
        Gtk.PolicyType.AUTOMATIC,
        Gtk.PolicyType.NEVER,
    )
    assert space.canvas_scroller.get_policy() == (
        Gtk.PolicyType.AUTOMATIC,
        Gtk.PolicyType.AUTOMATIC,
    )

    pen_button = space.tool_buttons["Pen"]
    pen_button.set_active(True)
    assert space.pen.enabled
    assert not space.tool_buttons["Eraser"].get_active()
    pen_button.set_active(False)
    assert not space.pen.enabled


def test_space_pen_and_eraser_are_persistent_exclusive_tools() -> None:
    panel = AnalysisPanel()
    space = panel._section_placeholders["Space"]
    pen_button = space.tool_buttons["Pen"]
    eraser_button = space.tool_buttons["Eraser"]

    assert isinstance(eraser_button, Gtk.ToggleButton)
    eraser_button.set_active(True)
    assert eraser_button.get_active()
    assert space.eraser.enabled
    assert not pen_button.get_active()

    eraser_button.set_active(False)
    assert not eraser_button.get_active()
    assert not space.eraser.enabled

    eraser_button.set_active(True)
    pen_button.set_active(True)
    assert pen_button.get_active()
    assert space.pen.enabled
    assert not eraser_button.get_active()
    assert not space.eraser.enabled

    pen_button.set_active(False)
    assert not space.pen.enabled


def test_space_undo_redo_buttons_follow_stroke_history() -> None:
    panel = AnalysisPanel()
    space = panel._section_placeholders["Space"]
    space.canvas.set_content_width(100)
    space.canvas.set_content_height(100)
    space.pen.set_enabled(True)
    space.pen._on_drag_begin(None, 10.0, 12.0)
    space.pen._on_drag_end(None, 5.0, 7.0)

    assert space.tool_buttons["Undo"].get_sensitive()
    space.tool_buttons["Undo"].emit("clicked")
    assert not space.pen.can_undo
    assert not space.tool_buttons["Undo"].get_sensitive()
    assert space.tool_buttons["Redo"].get_sensitive()

    space.tool_buttons["Redo"].emit("clicked")
    assert space.pen.can_undo
    assert space.tool_buttons["Undo"].get_sensitive()
    assert not space.tool_buttons["Redo"].get_sensitive()


def test_space_board_extends_when_scrolling_reaches_its_edge() -> None:
    panel = AnalysisPanel()
    space = panel._section_placeholders["Space"]
    adjustment = Gtk.Adjustment.new(250, 0, 500, 10, 250, 250)

    space._extend_canvas_for_scroll(adjustment, "height")

    assert space.canvas.get_content_height() == 250
    adjustment.set_value(250)
    space._extend_canvas_for_scroll(adjustment, "height")
    assert space.canvas.get_content_height() == 500


def test_analysis_zoom_controls_stay_visible_outside_scrolling_views() -> None:
    panel = AnalysisPanel()

    assert panel.zoom_out_button.get_parent() is panel.navigation_row
    assert panel.zoom_in_button.get_parent() is panel.navigation_row
    assert panel.zoom_out_button.get_next_sibling() is panel.zoom_in_button
    assert panel.navigation_row.get_parent() is panel
    assert panel.get_last_child().get_parent() is panel
    assert panel.get_last_child() is not panel.navigation_row

    call_graph = panel._section_placeholders["Call Graph"]
    panel.select_section("Call Graph")
    panel.zoom_in_button.emit("clicked")
    assert call_graph._zoom == 1.25

    complexity = panel._section_placeholders["Complexity"]
    panel.select_section("Complexity")
    panel.zoom_out_button.emit("clicked")
    assert complexity._zoom_level == -1


def test_analysis_navigation_scrolls_horizontally() -> None:
    panel = AnalysisPanel()
    scroller = panel.navigation_scroller

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
    scale, origin_x, origin_y = flowchart._graph_origin()

    flowchart._on_canvas_pressed(
        None,
        1,
        origin_x + (node.x + node.width / 2) * scale,
        origin_y + (node.y + node.height / 2) * scale,
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
    assert window.analysis_panel.get_size_request()[0] > 0
    assert not window.analysis_panel_visible()
    assert window.right_pane.get_end_child() is window._analysis_placeholder

    window.right_pane.set_position(500)
    window.show_analysis_panel()
    assert window.analysis_panel_visible()
    assert window.right_pane.get_end_child() is window.analysis_panel
    assert window.right_pane.get_position() == 0

    window.toggle_analysis_panel()
    assert not window.analysis_panel_visible()
    assert window.right_pane.get_end_child() is window._analysis_placeholder
