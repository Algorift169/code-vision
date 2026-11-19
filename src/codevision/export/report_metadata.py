from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class ReportMetadata:
    schema_version: str = "1.0"
    title: str = "CodeVision Analysis Report"
    project_name: str = "Untitled Project"
    project_root: str | None = None
    primary_language: str | None = None
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    app_name: str = "CodeVision"
    app_version: str = "0.1.0"
    analysis_status: str = "complete"
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def for_project(cls, project_root: Path | None = None, language: str | None = None) -> "ReportMetadata":
        root = str(project_root) if project_root is not None else None
        name = project_root.name if project_root is not None and project_root.name else "Untitled Project"
        return cls(project_name=name, project_root=root, primary_language=language)
