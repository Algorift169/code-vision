from __future__ import annotations

from pathlib import Path


class GraphRenderer:
    """Render flowchart graphs with the existing Cairo graph exporter."""

    def render_flowcharts(self, graphs: list[object], output_dir: Path) -> list[Path]:
        from ...graphs.graph_export import GraphExporter

        output_dir.mkdir(parents=True, exist_ok=True)
        rendered: list[Path] = []
        exporter = GraphExporter()
        for index, graph in enumerate(graphs):
            name = getattr(graph, "function_name", None) or f"flowchart-{index + 1}"
            safe_name = "".join(character if character.isalnum() or character in "-_" else "-" for character in str(name))
            path = output_dir / f"{safe_name}.svg"
            exporter.export_svg(graph, path)
            rendered.append(path)
        return rendered
