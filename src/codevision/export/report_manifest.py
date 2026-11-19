from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class ReportManifest:
    project: dict[str, Any] = field(default_factory=dict)
    export_timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    generated_formats: list[str] = field(default_factory=list)
    included_sections: list[str] = field(default_factory=list)
    graph_assets: list[str] = field(default_factory=list)
    files: list[dict[str, Any]] = field(default_factory=list)
    completeness_status: str = "unknown"
    errors: list[dict[str, str]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project": self.project,
            "export_timestamp": self.export_timestamp,
            "generated_formats": self.generated_formats,
            "included_sections": self.included_sections,
            "graph_assets": self.graph_assets,
            "files": self.files,
            "completeness_status": self.completeness_status,
            "errors": self.errors,
            "warnings": self.warnings,
        }
