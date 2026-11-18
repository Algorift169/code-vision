from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GraphTextLine:
    text: str
    x: float
    y: float
    font_size: float = 12.0
    alignment: str = "left"


@dataclass(frozen=True, slots=True)
class GraphNodeData:
    node_id: str
    title: str
    detail: str
    x: float
    y: float
    width: float
    height: float
    shape: str = "rectangle"
    fill_color: tuple[float, float, float, float] = (0.16, 0.48, 0.42, 0.20)
    stroke_color: tuple[float, float, float, float] = (0.16, 0.48, 0.42, 1.0)
    text_color: tuple[float, float, float, float] = (0.92, 0.94, 0.97, 1.0)
    text_lines: tuple[GraphTextLine, ...] = ()
    stroke_width: float = 1.8


@dataclass(frozen=True, slots=True)
class GraphEdgeData:
    source_id: str
    target_id: str
    label: str = ""


@dataclass(frozen=True, slots=True)
class GraphSnapshot:
    title: str
    nodes: tuple[GraphNodeData, ...]
    edges: tuple[GraphEdgeData, ...]


__all__ = [
    "GraphEdgeData",
    "GraphNodeData",
    "GraphSnapshot",
    "GraphTextLine",
]
