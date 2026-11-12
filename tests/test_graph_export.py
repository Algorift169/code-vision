import cairo

from codevision.graphs import FlowchartBuilder, GraphExporter, GraphLayout
from codevision.parser import SourceParser


def test_graph_exporter_writes_real_svg_png_and_pdf_without_mutating_graph(tmp_path) -> None:
    source = "int main() { if (x) { printf(\"yes\"); } else { return 0; } }"
    graph = FlowchartBuilder().build(
        SourceParser().parse(source, language="c"), source
    )
    GraphLayout.layout(graph)
    before = [(node.x, node.y, node.width, node.height) for node in graph.nodes]
    exporter = GraphExporter()

    svg_path = exporter.export_svg(graph, tmp_path / "flowchart.svg")
    png_path = exporter.export_png(graph, tmp_path / "flowchart.png")
    pdf_path = exporter.export_pdf(graph, tmp_path / "flowchart.pdf")

    assert svg_path.read_bytes().startswith(b"<?xml")
    assert b"<svg" in svg_path.read_bytes()
    assert png_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    image = cairo.ImageSurface.create_from_png(str(png_path))
    assert image.get_width() > 0 and image.get_height() > 0
    assert pdf_path.read_bytes().startswith(b"%PDF-")
    assert all(path.stat().st_size > 100 for path in (svg_path, png_path, pdf_path))
    assert [(node.x, node.y, node.width, node.height) for node in graph.nodes] == before