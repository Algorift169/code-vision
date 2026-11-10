from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class LanguageInfo:
    language_id: str
    display_name: str
    extensions: tuple[str, ...]


class LanguageRegistry:
    C = LanguageInfo("c", "C", (".c", ".h"))
    CPP = LanguageInfo(
        "cpp", "C++", (".cpp", ".cc", ".cxx", ".hpp", ".hh", ".hxx")
    )
    @classmethod
    def resolve(
        cls, language: str | None = None, file_path: str | Path | None = None
    ) -> LanguageInfo | None:
        if language is not None:
            normalized = language.strip().lower()
            aliases = {"c++": "cpp", "cxx": "cpp", "cc": "cpp"}
            normalized = aliases.get(normalized, normalized)
            if normalized == "c":
                return cls.C
            if normalized == "cpp":
                return cls.CPP
            return None
        if file_path is None:
            return None
        extension = Path(file_path).suffix.lower()
        return next(
            (
                info
                for info in (cls.C, cls.CPP)
                if extension in info.extensions
            ),
            None,
        )
