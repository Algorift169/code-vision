from __future__ import annotations

import textwrap

from .flowchart_ir import FlowchartGraph


class GraphLayout:
    """Deterministic top-to-bottom layout for flowchart graphs."""

    @staticmethod
    def layout(graph: FlowchartGraph) -> FlowchartGraph:
        base_x = 24.0
        base_y = 24.0
        layer_gap = 88.0
        max_node_width = 360.0
        for index, node in enumerate(graph.nodes):
            node.width = 136.0
            node.height = 52.0
            if node.kind.value in {"start", "end"}:
                node.width = 104.0
                node.height = 48.0
            elif node.kind.value in {"decision", "loop"}:
                node.width = 208.0
                node.height = 64.0
            label = " ".join(node.label.split())
            text_ratio = 0.55 if node.kind.value in {"decision", "loop"} else 1.0
            padding = 0.0 if text_ratio < 1.0 else 24.0
            desired_line_chars = max(1, (len(label) + 2) // 3)
            desired_width = (desired_line_chars * 7.2 + padding) / text_ratio
            node.width = min(max_node_width, max(node.width, desired_width))
            text_width = node.width * 0.55 if node.kind.value in {"decision", "loop"} else node.width - 24
            line_width = max(8, int(text_width / 7.2))
            display_lines = textwrap.wrap(
                label,
                width=line_width,
                break_long_words=True,
                break_on_hyphens=False,
            ) or [node.label]
            node.metadata["display_lines"] = display_lines
            if node.kind.value not in {"start", "end", "merge", "connector"}:
                node.height = max(node.height, 18.0 * len(display_lines) + 18.0)
            node.x = base_x + (148.0 - node.width) / 2
            node.y = base_y if index == 0 else graph.nodes[index - 1].y + graph.nodes[index - 1].height + 32.0

        node_by_id = {node.node_id: node for node in graph.nodes}
        for node in graph.nodes:
            if node.kind.value not in {"decision", "loop"}:
                continue
            labeled_edges = [
                edge
                for edge in graph.edges
                if edge.source_id == node.node_id and edge.branch_label
            ]
            branch_targets: list[str] = []
            for edge in labeled_edges:
                if edge.target_id not in branch_targets:
                    branch_targets.append(edge.target_id)
            if len(branch_targets) < 2:
                continue

            left_target = node_by_id.get(branch_targets[0])
            right_target = node_by_id.get(branch_targets[1])
            if left_target is None or right_target is None:
                continue
            branch_y = max(node.y + node.height + 38.0, left_target.y, right_target.y)
            left_target.x = node.x - 156.0
            right_target.x = node.x + node.width + 8.0
            left_target.y = branch_y
            right_target.y = branch_y
        return graph


__all__ = ["GraphLayout"]
