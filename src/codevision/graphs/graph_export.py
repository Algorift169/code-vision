from __future__ import annotations

import copy
import math
import textwrap
from pathlib import Path

import cairo

from .flowchart_ir import FlowchartGraph
from .graph_layout import GraphLayout


class GraphExporter:
    def export_svg(self, graph: FlowchartGraph, path: str | Path) -> Path:
        output = Path(path)
        graph, width, height, dx, dy = self._prepare(graph)
        surface = cairo.SVGSurface(str(output), width, height)
        self._draw(cairo.Context(surface), graph, dx, dy)
        surface.finish()
        return output

    def export_png(self, graph: FlowchartGraph, path: str | Path) -> Path:
        output = Path(path)
        graph, width, height, dx, dy = self._prepare(graph)
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        self._draw(cairo.Context(surface), graph, dx, dy)
        surface.write_to_png(str(output))
        return output

    def export_pdf(self, graph: FlowchartGraph, path: str | Path) -> Path:
        output = Path(path)
        graph, width, height, dx, dy = self._prepare(graph)
        surface = cairo.PDFSurface(str(output), width, height)
        self._draw(cairo.Context(surface), graph, dx, dy)
        surface.finish()
        return output

    @staticmethod
    def _prepare(graph: FlowchartGraph) -> tuple[FlowchartGraph, int, int, float, float]:
        rendered = copy.deepcopy(graph)
        GraphLayout.layout(rendered)
        padding = 32.0
        left = min(node.x for node in rendered.nodes)
        top = min(node.y for node in rendered.nodes)
        right = max(node.x + node.width for node in rendered.nodes)
        bottom = max(node.y + node.height for node in rendered.nodes)
        return (
            rendered,
            max(1, math.ceil(right - left + padding * 2)),
            max(1, math.ceil(bottom - top + padding * 2)),
            padding - left,
            padding - top,
        )

    @staticmethod
    def _route(nodes: list[object], source: object, target: object, index: int):
        source_center = source.x + source.width / 2
        target_center = target.x + target.width / 2
        start_y = source.y + source.height
        end_y = target.y - 9
        if abs(source_center - target_center) < 2 and end_y > start_y:
            return [(source_center, start_y), (target_center, end_y)]
        if end_y > start_y:
            middle_y = (start_y + end_y) / 2
            return [
                (source_center, start_y),
                (source_center, middle_y),
                (target_center, middle_y),
                (target_center, end_y),
            ]
        lane_x = max(node.x + node.width for node in nodes) + 24 + index % 5 * 8
        start = (source.x + source.width, source.y + source.height / 2)
        finish = (target.x + target.width, target.y + target.height / 2)
        return [start, (lane_x, start[1]), (lane_x, finish[1]), finish]

    @staticmethod
    def _arrow(context: cairo.Context, start: tuple[float, float], end: tuple[float, float]) -> None:
        angle = math.atan2(end[1] - start[1], end[0] - start[0])
        base_x = end[0] - 8 * math.cos(angle)
        base_y = end[1] - 8 * math.sin(angle)
        context.move_to(*end)
        context.line_to(base_x + 4 * math.sin(angle), base_y - 4 * math.cos(angle))
        context.line_to(base_x - 4 * math.sin(angle), base_y + 4 * math.cos(angle))
        context.close_path()
        context.fill()

    @classmethod
    def _draw(cls, context: cairo.Context, graph: FlowchartGraph, dx: float, dy: float) -> None:
        colors = {
            "start": (0.12, 0.63, 0.53), "end": (0.12, 0.63, 0.53),
            "process": (0.24, 0.52, 0.88), "decision": (0.94, 0.63, 0.12),
            "loop": (0.94, 0.63, 0.12), "function": (0.58, 0.38, 0.82),
            "input": (0.18, 0.66, 0.42), "output": (0.18, 0.66, 0.42),
            "return": (0.87, 0.34, 0.38), "break": (0.87, 0.34, 0.38),
            "continue": (0.87, 0.34, 0.38), "exception": (0.89, 0.43, 0.18),
            "merge": (0.35, 0.60, 0.68), "connector": (0.35, 0.60, 0.68),
        }
        context.translate(dx, dy)
        context.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        context.set_font_size(12)
        node_by_id = {node.node_id: node for node in graph.nodes}
        for index, edge in enumerate(graph.edges):
            source = node_by_id.get(edge.source_id)
            target = node_by_id.get(edge.target_id)
            if source is None or target is None:
                continue
            points = cls._route(graph.nodes, source, target, index)
            edge_color = (0.15, 0.62, 0.40) if edge.branch_label == "yes" else (
                (0.82, 0.31, 0.35) if edge.branch_label == "no" else (0.24, 0.55, 0.78)
            )
            context.set_source_rgba(*edge_color, 0.95)
            context.set_line_width(1.8)
            context.move_to(*points[0])
            for point in points[1:]:
                context.line_to(*point)
            context.stroke()
            cls._arrow(context, points[-2], points[-1])
            if edge.branch_label:
                context.move_to(
                    (points[0][0] + points[-1][0]) / 2 + 4,
                    (points[0][1] + points[-1][1]) / 2 - 4,
                )
                context.show_text(edge.branch_label.upper())
        for node in graph.nodes:
            cls._draw_node(context, node, colors.get(node.kind.value, colors["process"]))

    @staticmethod
    def _draw_node(context: cairo.Context, node: object, color: tuple[float, float, float]) -> None:
        x, y, width, height = node.x, node.y, node.width, node.height
        kind = node.kind.value
        context.set_source_rgba(*color, 0.18)
        context.set_line_width(1.8)
        if kind in {"start", "end"}:
            context.arc(x + width / 2, y + height / 2, height / 2, 0, math.tau)
        elif kind in {"decision", "loop"}:
            context.move_to(x + width / 2, y)
            context.line_to(x + width, y + height / 2)
            context.line_to(x + width / 2, y + height)
            context.line_to(x, y + height / 2)
            context.close_path()
        elif kind in {"input", "output"}:
            context.move_to(x + 16, y)
            context.line_to(x + width, y)
            context.line_to(x + width - 16, y + height)
            context.line_to(x, y + height)
            context.close_path()
        elif kind == "exception":
            context.move_to(x + 18, y)
            context.line_to(x + width - 18, y)
            context.line_to(x + width, y + height / 2)
            context.line_to(x + width - 18, y + height)
            context.line_to(x + 18, y + height)
            context.line_to(x, y + height / 2)
            context.close_path()
        elif kind in {"merge", "connector"}:
            context.arc(x + width / 2, y + height / 2, min(width, height) / 5, 0, math.tau)
        else:
            context.rectangle(x, y, width, height)
        context.fill_preserve()
        context.set_source_rgba(*color, 1)
        context.stroke()
        lines = node.metadata.get("display_lines") or textwrap.wrap(
            node.label, max(8, int((width - 24) / 7.2))
        )
        baseline = y + (height - 14 * len(lines)) / 2 + 11
        context.set_source_rgb(0.08, 0.1, 0.13)
        for line_index, line in enumerate(lines):
            extents = context.text_extents(line)
            text_x = x + (width - extents.width) / 2 - extents.x_bearing
            context.move_to(text_x, baseline + line_index * 14)
            context.show_text(line)


__all__ = ["GraphExporter"]
