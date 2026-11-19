from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class ExportContext:
    project_root: Path | None = None
    source: str | None = None
    source_file: Path | None = None
    language: str | None = None
    analysis: dict[str, Any] = field(default_factory=dict)
    graph_assets: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    selected_section: str | None = None
