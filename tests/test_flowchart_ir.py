from codevision.graphs import FlowchartEdge, FlowchartGraph, FlowchartNode, FlowchartNodeKind


def test_flowchart_ir_creates_valid_graph_objects() -> None:
    node_a = FlowchartNode(node_id="a", kind=FlowchartNodeKind.START, label="START")
    node_b = FlowchartNode(node_id="b", kind=FlowchartNodeKind.PROCESS, label="assign")
    edge = FlowchartEdge(edge_id="e1", source_id="a", target_id="b", edge_type="normal")
    graph = FlowchartGraph(
        graph_id="demo",
        source_file=None,
        language="python",
        nodes=[node_a, node_b],
        edges=[edge],
        entry="a",
        exit_nodes=["b"],
    )

    validation = graph.validate()
    assert validation.valid
    assert node_a.kind is FlowchartNodeKind.START
    assert edge.edge_type == "normal"
