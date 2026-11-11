from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class LanguageCapabilities:
    """Declared analyzer features a language adapter can provide."""

    parsing: bool = False
    ast: bool = False
    flowchart: bool = False
    call_graph: bool = False
    variable_flow: bool = False
    complexity: bool = False
    warnings: bool = False
    diagnostics: bool = False

    def as_tuple(self) -> tuple[str, ...]:
        return tuple(
            name
            for name, enabled in (
                ("parsing", self.parsing),
                ("ast", self.ast),
                ("flowchart", self.flowchart),
                ("call_graph", self.call_graph),
                ("variable_flow", self.variable_flow),
                ("complexity", self.complexity),
                ("warnings", self.warnings),
                ("diagnostics", self.diagnostics),
            )
            if enabled
        )


@dataclass(frozen=True, slots=True)
class LanguageAdapter:
    """A small adapter descriptor shared by the analyzer and parser layers."""

    language_id: str
    display_name: str
    extensions: tuple[str, ...]
    aliases: tuple[str, ...] = ()
    supports_parsing: bool = False
    capabilities: tuple[str, ...] = ()
    description: str = ""

    def matches_name(self, value: str | None) -> bool:
        if value is None:
            return False
        normalized = value.strip().lower().replace(" ", "")
        candidates = {self.language_id.lower(), *[alias.lower() for alias in self.aliases]}
        return normalized in candidates or normalized in {
            alias.lower().replace(" ", "") for alias in self.aliases
        }

    def matches_path(self, value: str | Path | None) -> bool:
        if value is None:
            return False
        suffix = Path(value).suffix.lower()
        return suffix in {ext.lower() for ext in self.extensions}

    @property
    def can_parse(self) -> bool:
        return self.supports_parsing

    @property
    def declared_capabilities(self) -> tuple[str, ...]:
        return self.capabilities
