from pathlib import Path

from codevision.graphs import FlowchartBuilder, FlowchartGraph, GraphValidationResult
from codevision.parser import SourceParser


def test_flowchart_builder_handles_sequential_and_return_nodes() -> None:
    result = SourceParser().parse("int main() { int x = 1; return x; }", language="c")
    graph = FlowchartBuilder().build(result)

    assert isinstance(graph, FlowchartGraph)
    assert graph.entry is not None
    assert any(node.kind.value == "start" for node in graph.nodes)
    assert any("return" in node.label.lower() for node in graph.nodes)
    assert graph.validate().valid


def test_flowchart_builder_creates_decision_branches_for_if_else() -> None:
    result = SourceParser().parse(
        "int main() { int x = 1; if (x > 0) { return 1; } else { return 0; } }",
        language="c",
    )
    graph = FlowchartBuilder().build(result)

    decision_nodes = [node for node in graph.nodes if node.kind.value == "decision"]
    assert decision_nodes
    assert any(edge.branch_label in {"yes", "no"} for edge in graph.edges)
    assert graph.validate().valid


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
