import pytest

from codevision.graphs import CallGraphBuilder
from codevision.parser import SourceParser
from codevision.ui.graphs import CallGraphView


def test_call_graph_resolves_calls_between_local_functions() -> None:
    source = (
        "int leaf() { return 1; } "
        "int middle() { return leaf(); } "
        "int root() { leaf(); return middle(); }"
    )
    result = SourceParser().parse(source, language="c")

    graph = CallGraphBuilder().build(result)

    nodes = {node.node_id: node.name for node in graph.nodes}
    edges = {
        (nodes[edge.source_id], nodes[edge.target_id]): len(edge.call_sites)
        for edge in graph.edges
    }
    assert set(nodes.values()) == {"leaf", "middle", "root"}
    assert edges == {("middle", "leaf"): 1, ("root", "leaf"): 1, ("root", "middle"): 1}


def test_call_graph_edges_show_call_expression_and_repeated_call_count() -> None:
    source = "int leaf() { return 1; } int root() { leaf(); return leaf(); }"
    result = SourceParser().parse(source, language="c")

    graph = CallGraphBuilder().build(result)

    assert len(graph.edges) == 1
    assert graph.edges[0].label == "leaf() x2"


def test_call_graph_layout_keeps_recursive_functions_on_separate_lanes() -> None:
    view = CallGraphView()
    view.set_source("int left() { return right(); } int right() { return left(); }", None, "c")

    left = next(node for node in view.graph.nodes if node.name == "left")
    right = next(node for node in view.graph.nodes if node.name == "right")

    assert (left.x, left.y) != (right.x, right.y)


def test_call_graph_arrows_have_label_space_and_terminate_at_callee() -> None:
    view = CallGraphView()
    view.set_source(
        "int parse() { return 1; } int main() { return parse(); }", None, "c"
    )
    source = next(node for node in view.graph.nodes if node.name == "main")
    target = next(node for node in view.graph.nodes if node.name == "parse")
    edge = next(
        item for item in view.graph.edges
        if item.source_id == source.node_id and item.target_id == target.node_id
    )

    points = view._edge_route(source, target, 0)

    assert target.x - source.x - source.width >= 20
    assert points[-1] == (target.x, target.y + target.height / 2)
    assert edge.label in {"parse()", "parse() x1"}


def test_call_graph_tracks_nested_function_scope_correctly() -> None:
    source = """
    def main():
        def nested():
            return helper()
        nested()

    def helper():
        return 1
    """
    result = SourceParser().parse(source, language="python")

    graph = CallGraphBuilder().build(result)

    assert {edge.source_id for edge in graph.edges if edge.target_id} == {next(node.node_id for node in graph.nodes if node.name == "main"), next(node.node_id for node in graph.nodes if node.name == "nested")}
    assert not any(
        edge.source_id == next(node.node_id for node in graph.nodes if node.name == "main")
        and edge.target_id == next(node.node_id for node in graph.nodes if node.name == "helper")
        for edge in graph.edges
    )
    assert any(
        edge.source_id == next(node.node_id for node in graph.nodes if node.name == "nested")
        and edge.target_id == next(node.node_id for node in graph.nodes if node.name == "helper")
        for edge in graph.edges
    )


def test_call_graph_resolves_same_name_functions_by_scope() -> None:
    source = """
    def process():
        return 0

    class A:
        def process(self):
            return 1

    def main():
        return process()
    """
    result = SourceParser().parse(source, language="python")

    graph = CallGraphBuilder().build(result)

    main = next(node for node in graph.nodes if node.name == "main")
    module_process = next(node for node in graph.nodes if node.name == "process" and "." not in node.qualified_name)
    class_process = next(node for node in graph.nodes if node.name == "process" and "." in node.qualified_name)

    assert {node.name for node in graph.nodes} == {"process", "main"}
    assert any(
        edge.source_id == main.node_id and edge.target_id == module_process.node_id
        for edge in graph.edges
    )
    assert not any(
        edge.source_id == main.node_id and edge.target_id == class_process.node_id
        for edge in graph.edges
    )


def test_call_graph_zoom_buttons_scale_canvas_and_keep_source_hit_testing() -> None:
    navigated = []
    view = CallGraphView(on_source_navigate=navigated.append)
    view.set_source(
        "int leaf() { return 1; } int main() { return leaf(); }", None, "c"
    )
    source = next(node for node in view.graph.nodes if node.name == "main")
    width_before = view.canvas.get_content_width()

    view.zoom_in_button.emit("clicked")

    assert view._zoom == 1.25
    assert view.canvas.get_content_width() >= width_before
    view._on_canvas_pressed(
        None,
        1,
        (source.x + source.width / 2) * view._zoom,
        (source.y + source.height / 2) * view._zoom,
    )
    assert navigated[0].node_type == "function_definition"

    view.zoom_out_button.emit("clicked")
    assert view._zoom == 1.0


def test_call_graph_supports_python_call_nodes() -> None:
    source = "def leaf():\n    return 1\ndef root():\n    return leaf()\n"
    result = SourceParser().parse(source, language="python")

    graph = CallGraphBuilder().build(result)

    assert [(graph.nodes[0].name, graph.nodes[1].name)] == [("leaf", "root")]
    assert len(graph.edges) == 1
    assert graph.edges[0].call_sites[0].node_type == "call"


@pytest.mark.parametrize(
    ("language", "source"),
    [
        ("javascript", "function leaf() { return 1; } function root() { return leaf(); }"),
        (
            "java",
            "class Sample { int leaf() { return 1; } int root() { return leaf(); } }",
        ),
    ],
)
def test_call_graph_resolves_calls_in_language_specific_asts(language, source) -> None:
    result = SourceParser().parse(source, language=language)

    graph = CallGraphBuilder().build(result)

    assert {node.name for node in graph.nodes} == {"leaf", "root"}
    assert len(graph.edges) == 1


def test_call_graph_node_click_navigates_to_function_source() -> None:
    navigated = []
    view = CallGraphView(on_source_navigate=navigated.append)
    view.set_source(
        "int leaf() { return 1; } int root() { return leaf(); }", None, "c"
    )
    root = next(node for node in view.graph.nodes if node.name == "root")

    view._on_canvas_pressed(
        None, 1, root.x + root.width / 2, root.y + root.height / 2
    )

    assert len(navigated) == 1
    assert navigated[0].node_type == "function_definition"