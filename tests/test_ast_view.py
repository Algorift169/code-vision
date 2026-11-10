from codevision.parser import SourceParser
from codevision.ui.analysis_panel import AnalysisPanel
from codevision.ui.ast_view import ASTView


def test_ast_section_uses_interactive_ast_view() -> None:
    panel = AnalysisPanel()
    panel.select_section("AST")

    assert isinstance(panel.views.get_visible_child(), ASTView)


def test_ast_view_populates_tree_and_search_navigates_to_node() -> None:
    navigated = []
    view = ASTView(on_source_navigate=navigated.append)
    result = SourceParser().parse("int main() { return 0; }", language="c")

    view._apply_result(0, "test-source", result)
    model = view._tree_model
    assert model is not None
    assert model.get_n_items() == 1

    root_row = model.get_item(0)
    root_row.set_expanded(True)
    assert model.get_n_items() > 1

    view.search_entry.set_text("return")
    view._on_search_changed(view.search_entry)

    assert view._selection is not None
    selected_row = view._selection.get_selected_item()
    assert selected_row is not None
    assert navigated
    assert navigated[-1].node_type == "return_statement"


def test_ast_view_restores_tree_for_unchanged_source() -> None:
    view = ASTView()
    result = SourceParser().parse("int main() { return 0; }", language="c")
    view._apply_result(0, "test-source", result)

    view._show_state("Parsing active source...")
    view._check_cache_or_parse(0, "test-source", "", None, None)

    assert view.content_stack.get_visible_child_name() == "tree"


def test_ast_view_empty_source_state_is_clear() -> None:
    view = ASTView()
    view.set_source(None, None)

    assert view.content_stack.get_visible_child_name() == "state"
    assert view._state_label.get_text() == "No source editor is active."
