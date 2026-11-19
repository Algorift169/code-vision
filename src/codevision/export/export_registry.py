from __future__ import annotations

from .formats.base_exporter import BaseExporter
from .formats.html_exporter import HTMLExporter
from .formats.json_exporter import JSONExporter
from .formats.markdown_exporter import MarkdownExporter
from .formats.txt_exporter import TXTExporter


class ExportRegistry:
    def __init__(self) -> None:
        self._exporters: dict[str, BaseExporter] = {}
        self.register("html", HTMLExporter())
        self.register("json", JSONExporter())
        self.register("md", MarkdownExporter())
        self.register("txt", TXTExporter())

    def register(self, format_name: str, exporter: BaseExporter) -> None:
        self._exporters[format_name.lower()] = exporter

    def get(self, format_name: str) -> BaseExporter:
        key = format_name.lower().lstrip(".")
        if key not in self._exporters:
            raise KeyError(f"Unsupported export format: {format_name}")
        return self._exporters[key]

    def formats(self) -> tuple[str, ...]:
        return tuple(sorted(self._exporters))
