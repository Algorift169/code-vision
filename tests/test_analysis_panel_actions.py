import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gtk

from codevision.actions import (
    change_color,
    clear_screen,
    duplicate_box,
    forward_full_graph,
    forward_to_space,
    remove,
    rename_box,
    select_all,
    select_multiple,
    show_complexity,
)
from codevision.actions.rename_box import _apply_item_name
from codevision.app.main_window import CodeVisionWindow
from codevision.actions.action import ANALYSIS_PANEL_ACTIONS
from codevision.actions.helpers import graph_snapshot_for
from codevision.ui.analysis_panel import AnalysisPanel
from codevision.ui.widgets.menu import ContextMenu
from codevision.ui.widgets.menu_context import MenuContext
from codevision.space.shape_item import ShapeItem
from codevision.shape import SHAPES


def test_right_click_context_shows_analysis_panel_actions_only() -> None:
    overlay = Gtk.Overlay()
    content = Gtk.Box()
    overlay.set_child(content)
    menu = ContextMenu(
        overlay,
        content,
        lambda _x, _y: MenuContext(
            widget=content,
            kind="analysis-panel",
        ),
    )

    menu._on_pressed(None, 1, 42.0, 68.0)

    visible_actions = [
        action_id
        for action_id, (button, _action) in menu._items.items()
        if button.get_visible()
    ]
    assert visible_actions == [
        action_id
        for action_id, _label, _icon, _action in ANALYSIS_PANEL_ACTIONS
    ]
    assert menu.get_visible()


def test_select_all_works_after_context_menu_dismissal_and_reopen() -> None:
    class TestWindow(Gtk.Window):
        click_inside_menu = True

        def is_click_inside_open_menu(self, _box, _x, _y):
            return self.click_inside_menu

        def is_click_on_active_menu_button(self, _box, _x, _y):
            return False

        def close_all_menus(self, except_menu=None):
            return False

    panel = AnalysisPanel()
    panel.select_section("Space")
    space = panel._section_placeholders["Space"]
    text_box = space.add_text_box("select every word")
    overlay = Gtk.Overlay()
    content = Gtk.Box()
    content.append(panel)
    overlay.set_child(content)
    window = TestWindow()
    window.set_child(overlay)
    context = MenuContext(
        widget=text_box.text_view,
        kind="analysis-panel",
        analysis_panel=panel,
    )
    menu = ContextMenu(overlay, content, lambda _x, _y: context)
    select_all_button = menu._items["panel-select-all"][0]

    menu._on_pressed(None, 1, 10.0, 10.0)
    menu._on_dismiss_pressed(None, 1, 10.0, 10.0)
    assert menu.get_visible()
    select_all_button.emit("clicked")
    buffer = text_box.buffer
    bounds = buffer.get_selection_bounds()
    assert bounds
    assert buffer.get_text(bounds[0], bounds[1], True) == "select every word"

    window.click_inside_menu = False
    menu._on_pressed(None, 1, 10.0, 10.0)
    menu._on_dismiss_pressed(None, 1, 300.0, 300.0)
    assert not menu.get_visible()
    buffer.place_cursor(buffer.get_start_iter())

    menu._on_pressed(None, 1, 10.0, 10.0)
    select_all_button.emit("clicked")
    bounds = buffer.get_selection_bounds()
    assert bounds
    assert buffer.get_text(bounds[0], bounds[1], True) == "select every word"


def test_analysis_panel_actions_are_scoped_to_analysis_context() -> None:
    panel = AnalysisPanel()
    panel_context = MenuContext(
        widget=Gtk.Label(label="overview"),
        kind="analysis-panel",
        analysis_panel=panel,
    )
    window_context = MenuContext(
        widget=Gtk.Label(label="overview"),
        kind="window",
        analysis_panel=panel,
    )

    for _action_id, _label, _icon, action in ANALYSIS_PANEL_ACTIONS:
        assert not action.is_enabled(window_context)

    assert show_complexity.is_enabled(panel_context)
    assert not clear_screen.is_enabled(panel_context)
    assert not duplicate_box.is_enabled(panel_context)
    assert not change_color.is_enabled(panel_context)
    assert not rename_box.is_enabled(panel_context)
    assert not remove.is_enabled(panel_context)
    assert not select_all.is_enabled(panel_context)
    assert not forward_full_graph.is_enabled(panel_context)
    assert select_multiple.is_enabled(panel_context)


def test_space_actions_enable_for_board_items_only_in_space() -> None:
    panel = AnalysisPanel()
    space = panel._section_placeholders["Space"]
    text_box = space.add_text_box("notes")
    context = MenuContext(
        widget=text_box.text_view,
        kind="analysis-panel",
        analysis_panel=panel,
    )

    panel.select_section("Space")
    assert not select_multiple.is_enabled(context)
    assert clear_screen.is_enabled(context)
    assert duplicate_box.is_enabled(context)
    assert change_color.is_enabled(context)
    assert rename_box.is_enabled(context)
    assert remove.is_enabled(context)

    panel.select_section("Overview")
    assert not clear_screen.is_enabled(context)
    assert not duplicate_box.is_enabled(context)
    assert not change_color.is_enabled(context)
    assert not rename_box.is_enabled(context)
    assert not remove.is_enabled(context)


def test_rename_action_is_available_for_shapes() -> None:
    panel = AnalysisPanel()
    space = panel._section_placeholders["Space"]
    panel.select_section("Space")
    item = space.add_shape(SHAPES[0])
    context = MenuContext(
        widget=item,
        kind="analysis-panel",
        analysis_panel=panel,
    )

    assert isinstance(item, ShapeItem)
    assert rename_box.is_enabled(context)
    item.set_title("Orders API")
    assert item.title == "Orders API"
    assert item.title_label.get_text() == "Orders API"
    assert item.title_label.get_visible()


def test_renaming_imported_item_only_changes_its_space_display_name(tmp_path) -> None:
    file_path = tmp_path / "report.txt"
    original_contents = "keep file unchanged"
    file_path.write_text(original_contents, encoding="utf-8")

    panel = AnalysisPanel()
    space = panel._section_placeholders["Space"]
    panel.select_section("Space")
    imported = space.import_files([file_path])[0]

    _apply_item_name(imported, "Project Report")

    assert imported.display_name == "Project Report"
    assert imported.path == file_path
    assert file_path.name == "report.txt"
    assert file_path.read_text(encoding="utf-8") == original_contents


def test_duplicate_box_copies_text_and_imported_file_metadata(tmp_path) -> None:
    panel = AnalysisPanel()
    space = panel._section_placeholders["Space"]
    panel.select_section("Space")
    text_box = space.add_text_box("copy me", (10.0, 20.0))
    text_context = MenuContext(
        widget=text_box.text_view,
        kind="analysis-panel",
        analysis_panel=panel,
    )

    duplicate_box.run(text_context)

    duplicate_text = space.text_boxes[-1]
    assert duplicate_text is not text_box
    assert (duplicate_text.x, duplicate_text.y) == (30.0, 40.0)
    assert duplicate_text.buffer.get_text(
        duplicate_text.buffer.get_start_iter(),
        duplicate_text.buffer.get_end_iter(),
        True,
    ) == "copy me"

    file_path = tmp_path / "notes.docx"
    file_path.write_bytes(b"document")
    imported = space.import_files([file_path], (50.0, 60.0))[0]
    imported.set_display_name("Renamed document")
    file_context = MenuContext(
        widget=imported,
        kind="analysis-panel",
        analysis_panel=panel,
    )

    duplicate_box.run(file_context)
    duplicate_import = space.import_items[-1]
    assert duplicate_import.path == imported.path
    assert duplicate_import.display_name == "Renamed document"
    assert (duplicate_import.x, duplicate_import.y) == (70.0, 80.0)


def test_clear_screen_only_clears_space_board(tmp_path) -> None:
    panel = AnalysisPanel()
    space = panel._section_placeholders["Space"]
    text_box = space.add_text_box("keep until Space is active")
    file_path = tmp_path / "notes.docx"
    file_path.write_bytes(b"document")
    space.import_files([file_path])
    space.tool_buttons["Pen"].set_active(True)
    space.pen._on_drag_begin(None, 10.0, 10.0)
    space.pen._on_drag_end(None, 5.0, 5.0)
    context = MenuContext(
        widget=text_box.text_view,
        kind="analysis-panel",
        analysis_panel=panel,
    )

    clear_screen.run(context)
    assert space.text_boxes == [text_box]
    assert len(space.import_items) == 1
    assert space.pen.strokes

    panel.select_section("Space")
    clear_screen.run(context)
    assert space.text_boxes == []
    assert space.import_items == []
    assert space.pen.strokes == []
    assert space.pen.can_undo
    space.pen.undo()
    assert space.pen.strokes


def test_change_color_opens_palette_for_the_target_text_box(monkeypatch) -> None:
    panel = AnalysisPanel()
    space = panel._section_placeholders["Space"]
    panel.select_section("Space")
    text_box = space.add_text_box("recolor")
    context = MenuContext(
        widget=text_box.text_view,
        kind="analysis-panel",
        analysis_panel=panel,
    )
    opened_for = []
    monkeypatch.setattr(space, "open_color_palette_for", opened_for.append)

    change_color.run(context)

    assert opened_for == [text_box]


def test_remove_deletes_only_the_clicked_space_item() -> None:
    panel = AnalysisPanel()
    space = panel._section_placeholders["Space"]
    panel.select_section("Space")
    target = space.add_text_box("remove")
    remaining = space.add_text_box("keep")
    context = MenuContext(
        widget=target.text_view,
        kind="analysis-panel",
        analysis_panel=panel,
    )

    remove.run(context)

    assert target not in space.text_boxes
    assert remaining in space.text_boxes


def test_forward_to_space_adds_analyzed_source_and_complexity_navigates() -> None:
    from pathlib import Path

    panel = AnalysisPanel()
    panel.set_source("int main() { return 0; }", Path("main.c"), "c")
    context = MenuContext(
        widget=panel,
        kind="analysis-panel",
        analysis_panel=panel,
    )

    forward_to_space.run(context)
    assert panel.current_section == "Space"
    space = panel._section_placeholders["Space"]
    assert len(space.text_boxes) == 1
    assert space.text_boxes[0].buffer.get_char_count() == len(panel.source_text)

    show_complexity.run(context)
    assert panel.current_section == "Complexity"


def test_forward_to_space_uses_the_right_clicked_flowchart_node() -> None:
    from pathlib import Path

    panel = AnalysisPanel()
    panel.set_source(
        "int main() { int value = 2; if (value) value++; return value; }",
        Path("main.c"),
        "c",
    )
    panel.select_section("Flowchart")
    view = panel._section_placeholders["Flowchart"]
    node = next(item for item in view.graph.nodes if item.kind.value == "decision")
    scale, origin_x, origin_y = view._graph_origin()
    position = (
        (node.x + node.width / 2) * scale + origin_x,
        (node.y + node.height / 2) * scale + origin_y,
    )
    context = MenuContext(
        widget=view.canvas,
        kind="analysis-panel",
        analysis_panel=panel,
        analysis_position=position,
    )

    assert forward_to_space.is_enabled(context)
    forward_to_space.run(context)

    space = panel._section_placeholders["Space"]
    assert len(space.graph_items) == 1
    forwarded = space.graph_items[0]
    assert forwarded.title == node.label
    assert forwarded.node.detail == (
        node.source_text.strip()
        or f"{node.kind.value} · Line {node.line or '?'}"
    )
    assert forwarded.node.shape == "diamond"
    color = view._NODE_COLORS[node.kind.value]
    assert forwarded.node.fill_color == (*color, 0.20)
    selected = (
        view._all_nodes_selected or node.node_id == view._selected_node_id
    )
    assert forwarded.node.stroke_color == (
        (1.0, 0.88, 0.28, 1.0) if selected else (*color, 1.0)
    )
    assert forwarded.node.text_lines

    space._dragged_import_item = forwarded
    space._import_drag_origin = (forwarded.x, forwarded.y)
    space._on_import_drag_update(None, 20.0, 10.0)
    assert (forwarded.x, forwarded.y) == (44.0, 34.0)


def test_forward_full_flowchart_to_space_creates_nodes_and_edges() -> None:
    from pathlib import Path

    panel = AnalysisPanel()
    panel.set_source(
        "int main() { int value = 2; if (value) value++; return value; }",
        Path("main.c"),
        "c",
    )
    panel.select_section("Flowchart")
    view = panel._section_placeholders["Flowchart"]
    context = MenuContext(
        widget=view.canvas,
        kind="analysis-panel",
        analysis_panel=panel,
    )

    assert forward_full_graph.is_enabled(context)
    forward_full_graph.run(context)

    space = panel._section_placeholders["Space"]
    assert len(space.graph_items) == len(view.graph.nodes)
    assert space.text_boxes
    assert space.text_boxes[-1].buffer.get_text(
        space.text_boxes[-1].buffer.get_start_iter(),
        space.text_boxes[-1].buffer.get_end_iter(),
        True,
    ) == "main"
    assert len(space.pen.strokes) >= len(view.graph.edges)


def test_select_all_selects_every_node_in_the_current_graph() -> None:
    from pathlib import Path

    panel = AnalysisPanel()
    panel.set_source("int main() { return 0; }", Path("main.c"), "c")
    panel.select_section("Flowchart")
    view = panel._section_placeholders["Flowchart"]
    context = MenuContext(
        widget=view.canvas,
        kind="analysis-panel",
        analysis_panel=panel,
    )

    assert select_all.is_enabled(context)
    select_all.run(context)

    assert view._all_nodes_selected


def test_select_multiple_forwards_selected_nodes_when_enter_is_pressed() -> None:
    from pathlib import Path

    panel = AnalysisPanel()
    panel.set_source(
        "int main() { int value = 2; if (value) value++; return value; }",
        Path("main.c"),
        "c",
    )
    panel.select_section("Flowchart")
    view = panel._section_placeholders["Flowchart"]
    status_messages = []
    context = MenuContext(
        widget=view.canvas,
        kind="analysis-panel",
        analysis_panel=panel,
        set_status=status_messages.append,
    )

    assert select_multiple.is_enabled(context)
    select_multiple.run(context)
    session = panel._multi_select_session
    snapshot = graph_snapshot_for(context)
    assert snapshot is not None
    selected_nodes = snapshot.nodes[:2]
    for node in selected_nodes:
        selection = select_multiple._Selection(
            ("Flowchart", f"node:{node.node_id}"),
            node,
            None,
            None,
        )
        session.selected[selection.key] = selection
    text_selection = select_multiple._Selection(
        ("Flowchart", "widget:test-text"),
        None,
        "A selected text item",
        None,
    )
    session.selected[text_selection.key] = text_selection
    session._refresh_highlights()

    assert view._multi_select_node_ids == {
        node.node_id for node in selected_nodes
    }
    assert session._on_key_pressed(
        None, Gdk.KEY_Return, 0, Gdk.ModifierType(0)
    )

    space = panel._section_placeholders["Space"]
    assert panel.current_section == "Space"
    assert [item.node for item in space.graph_items] == list(selected_nodes)
    assert space.text_boxes[0].buffer.get_text(
        space.text_boxes[0].buffer.get_start_iter(),
        space.text_boxes[0].buffer.get_end_iter(),
        True,
    ) == "A selected text item"
    assert len(status_messages) == 2


def test_full_graph_forward_supports_call_variable_and_complexity_views() -> None:
    from pathlib import Path

    panel = AnalysisPanel()
    panel.set_source(
        "int leaf() { return 1; } "
        "int main() { int value = leaf(); return value; }",
        Path("main.c"),
        "c",
    )
    for section in ("Call Graph", "Var Flow", "Complexity"):
        panel.select_section(section)
        view = panel._section_placeholders[section]
        context = MenuContext(
            widget=view,
            kind="analysis-panel",
            analysis_panel=panel,
        )
        snapshot = graph_snapshot_for(context)

        assert snapshot is not None
        assert snapshot.nodes
        assert forward_full_graph.is_enabled(context)
        forward_full_graph.run(context)
        assert panel.current_section == "Space"


def test_dependency_graph_node_and_full_graph_forward_to_space(tmp_path) -> None:
    source_dir = tmp_path / "src"
    source_dir.mkdir()
    (source_dir / "main.py").write_text("from .helper import value\n", encoding="utf-8")
    (source_dir / "helper.py").write_text("value = 1\n", encoding="utf-8")
    panel = AnalysisPanel()
    panel.set_project_root(tmp_path)
    panel.select_section("Dependency")
    view = panel._section_placeholders["Dependency"]
    snapshot_context = MenuContext(
        widget=view.canvas,
        kind="analysis-panel",
        analysis_panel=panel,
    )
    snapshot = graph_snapshot_for(snapshot_context)

    assert snapshot is not None
    assert snapshot.nodes
    node = view._nodes[0]
    origin_x, origin_y = view._origin()
    position = (
        node.x * view._zoom + origin_x + view._pan[0]
        + view.NODE_WIDTH / 2 * view._zoom,
        node.y * view._zoom + origin_y + view._pan[1]
        + view.NODE_HEIGHT / 2 * view._zoom,
    )
    node_context = MenuContext(
        widget=view.canvas,
        kind="analysis-panel",
        analysis_panel=panel,
        analysis_position=position,
    )
    forward_to_space.run(node_context)
    assert panel._section_placeholders["Space"].graph_items[0].title == node.label

    panel.select_section("Dependency")
    forward_full_graph.run(snapshot_context)
    assert len(panel._section_placeholders["Space"].graph_items) == (
        len(snapshot.nodes) + 1
    )


def test_ast_select_all_and_full_graph_forward(tmp_path) -> None:
    from codevision.parser import SourceParser

    panel = AnalysisPanel()
    view = panel._section_placeholders["AST"]
    result = SourceParser().parse("int main() { return 0; }", language="c")
    view._apply_result(view._generation, "test-source", result)
    panel.select_section("AST")
    root_row = view._tree_model.get_item(0)
    expander = Gtk.TreeExpander()
    expander.set_list_row(root_row)
    clicked_context = MenuContext(
        widget=expander,
        kind="analysis-panel",
        analysis_panel=panel,
    )
    forward_to_space.run(clicked_context)
    assert panel._section_placeholders["Space"].graph_items[0].title == (
        result.root.display_name
    )

    panel.select_section("AST")
    context = MenuContext(
        widget=view,
        kind="analysis-panel",
        analysis_panel=panel,
    )

    snapshot = graph_snapshot_for(context)
    assert snapshot is not None
    assert snapshot.nodes
    assert select_all.is_enabled(context)
    select_all.run(context)
    assert view._all_nodes_selected

    existing_graph_items = len(panel._section_placeholders["Space"].graph_items)
    forward_full_graph.run(context)
    assert len(panel._section_placeholders["Space"].graph_items) == (
        existing_graph_items + len(snapshot.nodes)
    )


def test_select_all_selects_all_complexity_rows(tmp_path) -> None:
    panel = AnalysisPanel()
    panel.set_source(
        "int first() { return 1; } int second() { return 2; }",
        tmp_path / "main.c",
        "c",
    )
    panel.select_section("Complexity")
    view = panel._section_placeholders["Complexity"]
    context = MenuContext(
        widget=view.list_box,
        kind="analysis-panel",
        analysis_panel=panel,
    )

    assert select_all.is_enabled(context)
    select_all.run(context)

    assert len(view.list_box.get_selected_rows()) == len(view._filtered_functions)


def test_forward_to_space_hits_a_node_in_the_call_graph() -> None:
    from pathlib import Path

    panel = AnalysisPanel()
    panel.set_source(
        "int leaf() { return 1; } int main() { return leaf(); }",
        Path("main.c"),
        "c",
    )
    panel.select_section("Call Graph")
    view = panel._section_placeholders["Call Graph"]
    node = next(item for item in view.graph.nodes if item.name == "main")
    origin_x, origin_y = view._graph_origin()
    position = (
        node.x * view._zoom + origin_x + view._pan_offset[0]
        + node.width * view._zoom / 2,
        node.y * view._zoom + origin_y + view._pan_offset[1]
        + node.height * view._zoom / 2,
    )
    context = MenuContext(
        widget=view.canvas,
        kind="analysis-panel",
        analysis_panel=panel,
        analysis_position=position,
    )

    forward_to_space.run(context)

    space = panel._section_placeholders["Space"]
    assert space.graph_items[0].title == (node.qualified_name or node.name)


def test_main_window_classifies_panel_descendant_as_analysis_context() -> None:
    analysis_panel = Gtk.Box()
    target = Gtk.Label(label="analysis content")
    analysis_panel.append(target)

    class ContextRoot:
        def pick(self, _x: float, _y: float, _flags: Gtk.PickFlags) -> Gtk.Widget:
            return target

        @staticmethod
        def translate_coordinates(
            _target: Gtk.Widget, x: float, y: float
        ) -> tuple[float, float]:
            return x - 5.0, y - 7.0

    class DummyWindow:
        _is_within = staticmethod(CodeVisionWindow._is_within)

        def __init__(self) -> None:
            self._context_menu_root = ContextRoot()
            self.analysis_panel = analysis_panel

        def _generic_menu_context(self, widget: Gtk.Widget) -> MenuContext:
            return MenuContext(widget=widget, kind="window")

    context = CodeVisionWindow._window_menu_context_at(
        DummyWindow(), 0.0, 0.0
    )

    assert context.kind == "analysis-panel"
    assert context.widget is target
    assert context.analysis_position == (-5.0, -7.0)
