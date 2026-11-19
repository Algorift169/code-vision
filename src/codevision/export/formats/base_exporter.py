from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..report_builder import ReportModel


@dataclass(slots=True)
class ExportMetadata:
    format: str
    path: Path
    size_bytes: int = 0
    included_sections: list[str] = field(default_factory=list)
    generated_graph_assets: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class BaseExporter(ABC):
    format_name = "unknown"
    extension = ".bin"

    @abstractmethod
    def export(self, report: ReportModel, output_path: Path, assets_dir: Path | None = None) -> ExportMetadata:
        raise NotImplementedError

    def validate(self, report: ReportModel, output_path: Path) -> None:
        if report is None:
            raise ValueError("A report is required")
        if not report.sections:
            raise ValueError("The report contains no sections")
        if output_path.suffix.lower() not in (self.extension,):
            raise ValueError(f"Expected {self.extension} output, got {output_path.suffix}")

    def prepare_output(self, output_path: Path) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
