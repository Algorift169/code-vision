from codevision.graphs import FlowchartBuilder, GraphLayout
from codevision.parser import SourceParser
from codevision.ui.graphs.flowchart_view import FlowchartView


def test_layout_compacts_nodes_and_separates_decision_branches() -> None:
    source = "int main() { if (x > 0) { return 1; } else { return 0; } }"
    graph = GraphLayout.layout(
        FlowchartBuilder().build(SourceParser().parse(source, language="c"))
    )

    decision = next(node for node in graph.nodes if node.kind.value == "decision")
    branches = [
        edge
        for edge in graph.edges
        if edge.source_id == decision.node_id and edge.branch_label
    ]
    branch_nodes = [next(node for node in graph.nodes if node.node_id == edge.target_id) for edge in branches]

    assert all(node.width <= 360 and node.height >= 48 for node in graph.nodes)
    assert len(branch_nodes) == 2
    assert branch_nodes[0].y == branch_nodes[1].y
    assert branch_nodes[0].x < branch_nodes[1].x


def test_edge_routes_avoid_unrelated_node_boxes() -> None:
    source = "int main() { if (x > 0) { return 1; } else { return 0; } }"
    graph = GraphLayout.layout(
        FlowchartBuilder().build(SourceParser().parse(source, language="c"))
    )
    view = FlowchartView()
    nodes = {node.node_id: node for node in graph.nodes}
    graph_left = min(node.x for node in graph.nodes)
    graph_right = max(node.x + node.width for node in graph.nodes)

    for edge_index, edge in enumerate(graph.edges):
        source_node = nodes[edge.source_id]
        target_node = nodes[edge.target_id]
        points, _arrow = view._edge_route(
            graph.nodes,
            source_node,
            target_node,
            graph_left,
            graph_right,
            edge_index,
        )
        for (x1, y1), (x2, y2) in zip(points, points[1:]):
            for node in graph.nodes:
                if node.node_id in {source_node.node_id, target_node.node_id}:
                    continue
                if (
                    x1 == x2
                    and node.x < x1 < node.x + node.width
                    and max(min(y1, y2), node.y)
                    < min(max(y1, y2), node.y + node.height)
                ):
                    raise AssertionError(f"vertical route crossed {node.node_id}")
                if (
                    y1 == y2
                    and node.y < y1 < node.y + node.height
                    and max(min(x1, x2), node.x)
                    < min(max(x1, x2), node.x + node.width)
                ):
                    raise AssertionError(f"horizontal route crossed {node.node_id}")


def test_graph_transform_centers_full_graph_in_available_canvas_width() -> None:
    source = "int main() { if (x > 0) { return 1; } else { return 0; } }"
    graph = GraphLayout.layout(
        FlowchartBuilder().build(SourceParser().parse(source, language="c"))
    )
    scale, origin_x = FlowchartView._graph_transform(graph, 480)
    left = min(node.x for node in graph.nodes) * scale + origin_x
    right = max(node.x + node.width for node in graph.nodes) * scale + origin_x

    assert scale < 1
    assert abs((left + right) / 2 - 240) < 1


def test_long_condition_is_complete_and_wrapped_inside_its_node() -> None:
    condition = " && ".join(f"feature_flag_{index:02d}" for index in range(12))
    source = f"int main() {{ if ({condition}) return 1; return 0; }}"
    result = SourceParser().parse(source, language="c")
    graph = GraphLayout.layout(FlowchartBuilder().build(result, source=source))
    decision = next(node for node in graph.nodes if node.kind.value == "decision")

    assert condition in decision.label
    assert "…" not in decision.label
    assert decision.width > 208
    assert len(decision.metadata["display_lines"]) > 1
    assert max(map(len, decision.metadata["display_lines"])) <= 50
