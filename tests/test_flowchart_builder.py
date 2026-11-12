from pathlib import Path

import pytest

from codevision.graphs import FlowchartBuilder, FlowchartGraph, GraphValidationResult
from codevision.parser import SourceParser


def test_flowchart_builder_handles_sequential_and_return_nodes() -> None:
    result = SourceParser().parse(
        "int main() { int x = 1; return x; x = 2; }", language="c"
    )
    graph = FlowchartBuilder().build(result)

    assert isinstance(graph, FlowchartGraph)
    assert graph.entry is not None
    assert any(node.kind.value == "start" for node in graph.nodes)
    assert any("return" in node.label.lower() for node in graph.nodes)
    assert not any("x = 2" in node.label for node in graph.nodes)
    assert graph.validate().valid


def test_flowchart_builder_creates_decision_branches_for_if_else() -> None:
    result = SourceParser().parse(
        "int main() { int x = 1; if (x > 0) { return 1; } else { return 0; } }",
        language="c",
    )
    graph = FlowchartBuilder().build(result)

    decision_nodes = [node for node in graph.nodes if node.kind.value == "decision"]
    assert decision_nodes
    branch_edges = [
        edge for edge in graph.edges
        if edge.source_id == decision_nodes[0].node_id and edge.branch_label
    ]
    assert {edge.branch_label for edge in branch_edges} == {"yes", "no"}
    assert graph.validate().valid


def test_flowchart_builder_routes_loop_control_and_omits_unreachable_code() -> None:
    source = (
        "int main() { int i = 0; while (i < 10) { "
        "if (i == 5) break; i++; continue; i = 99; } return i; }"
    )
    result = SourceParser().parse(source, language="c")
    graph = FlowchartBuilder().build(result, source)

    loop = next(node for node in graph.nodes if node.kind.value == "loop")
    break_node = next(node for node in graph.nodes if node.kind.value == "break")
    loop_back_edges = [edge for edge in graph.edges if edge.edge_type == "loop-back"]
    break_edge = next(edge for edge in graph.edges if edge.edge_type == "break")

    assert loop_back_edges
    assert all(edge.target_id == loop.node_id for edge in loop_back_edges)
    assert break_edge.source_id == break_node.node_id
    assert break_edge.target_id != loop.node_id
    assert not any("99" in node.label for node in graph.nodes)
    assert graph.validate().valid


def test_flowchart_builder_supports_python_functions_and_output_calls() -> None:
    source = "def choose(value):\n    if value:\n        print(value)\n    else:\n        return 0\n    return 1\n"
    result = SourceParser().parse(source, language="python")
    graph = FlowchartBuilder().build(result, source)

    assert graph.function_name == "choose"
    assert any(node.kind.value == "decision" for node in graph.nodes)
    assert any(node.kind.value == "output" for node in graph.nodes)
    assert any(node.kind.value == "return" for node in graph.nodes)
    assert not any("unsupported" in node.metadata for node in graph.nodes)
    assert graph.validate().valid


def test_flowchart_builder_can_build_each_function_separately() -> None:
    source = "int first() { return 1; } int second() { return 2; }"
    result = SourceParser().parse(source, language="c")

    graphs = FlowchartBuilder().build_all(result, source)

    assert [graph.function_name for graph in graphs] == ["first", "second"]
    assert all(graph.validate().valid for graph in graphs)


@pytest.mark.parametrize(
    ("language", "source"),
    [
        ("c", "int main() { if (ready) return 1; return 0; }"),
        ("cpp", "int main() { if (ready) return 1; return 0; }"),
        (
            "python",
            "def run(ready):\n    if ready:\n        return 1\n    return 0\n",
        ),
        (
            "java",
            "class Sample { int run(boolean ready) { if (ready) return 1; return 0; } }",
        ),
        ("javascript", "function run(ready) { if (ready) return 1; return 0; }"),
        (
            "typescript",
            "function run(ready: boolean): number { if (ready) return 1; return 0; }",
        ),
    ],
)
def test_flowchart_builder_handles_priority_languages(language, source) -> None:
    result = SourceParser().parse(source, language=language)
    graphs = FlowchartBuilder().build_all(result, source)

    assert graphs
    assert any(
        node.kind.value == "decision"
        for graph in graphs
        for node in graph.nodes
    )
    assert all(graph.validate().valid for graph in graphs)


def test_graph_validation_flags_missing_target() -> None:
    graph = FlowchartGraph(
        graph_id="broken",
        source_file=Path("example.c"),
        language="c",
        nodes=[],
        edges=["missing-target"],
        entry=None,
    )

    validation = graph.validate()
    assert isinstance(validation, GraphValidationResult)
    assert not validation.valid
    assert validation.issues


def test_graph_validation_flags_duplicate_edges_and_warns_on_unreachable_nodes() -> None:
    from codevision.graphs import FlowchartEdge, FlowchartNode, FlowchartNodeKind

    graph = FlowchartGraph(
        graph_id="unreachable",
        source_file=None,
        language="c",
        nodes=[
            FlowchartNode("start", FlowchartNodeKind.START, "START"),
            FlowchartNode("end", FlowchartNodeKind.END, "END"),
            FlowchartNode("isolated", FlowchartNodeKind.PROCESS, "isolated"),
        ],
        edges=[
            FlowchartEdge("edge", "start", "end"),
            FlowchartEdge("edge", "start", "end"),
        ],
        entry="start",
        exit_nodes=["end"],
    )

    validation = graph.validate()

    assert not validation.valid
    assert any("duplicate edge id" in issue for issue in validation.issues)
    assert any("isolated" in warning for warning in validation.warnings)
