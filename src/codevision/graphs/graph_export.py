from __future__ import annotations

from pathlib import Path

from .flowchart_ir import FlowchartGraph


class GraphExporter:
    def export_svg(self, graph: FlowchartGraph, path: str | Path) -> Path:
        output = Path(path)
        output.write_text("<svg />", encoding="utf-8")
        return output

    def export_png(self, graph: FlowchartGraph, path: str | Path) -> Path:
        output = Path(path)
        output.write_bytes(b"")
        return output

    def export_pdf(self, graph: FlowchartGraph, path: str | Path) -> Path:
        output = Path(path)
        output.write_bytes(b"%PDF-1.4\n")
        return output


__all__ = ["GraphExporter"]
