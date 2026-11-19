from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

SectionStatus = Literal["performed", "no-findings", "not-performed", "unavailable", "failed"]


@dataclass(slots=True)
class ReportSection:
    section_id: str
    title: str
    description: str = ""
    status: SectionStatus = "not-performed"
    content: dict[str, Any] = field(default_factory=dict)
    tables: list[dict[str, Any]] = field(default_factory=list)
    code_blocks: list[dict[str, Any]] = field(default_factory=list)
    graph_references: list[dict[str, Any]] = field(default_factory=list)
    source_references: list[dict[str, Any]] = field(default_factory=list)
    child_sections: list["ReportSection"] = field(default_factory=list)

    def record_count(self) -> int:
        count = 0
        for table in self.tables:
            count += len(table.get("rows", []))
        for code in self.code_blocks:
            count += 1 if code.get("code") not in (None, "") else 0
        count += len(self.graph_references)
        count += len(self.source_references)
        return count
