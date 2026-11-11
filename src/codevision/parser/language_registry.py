from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class LanguageInfo:
    language_id: str
    display_name: str
    extensions: tuple[str, ...]
    aliases: tuple[str, ...] = ()
    supports_parsing: bool = True
    capabilities: tuple[str, ...] = ()


class LanguageRegistry:
    C = LanguageInfo(
        "c",
        "C",
        (".c", ".h"),
        supports_parsing=True,
        capabilities=(
            "ast",
            "flowchart",
            "call_graph",
            "variable_flow",
            "complexity",
            "warnings",
            "diagnostics",
        ),
    )
    CPP = LanguageInfo(
        "cpp",
        "C++",
        (".cpp", ".cc", ".cxx", ".hpp", ".hh", ".hxx"),
        aliases=("c++", "cxx", "cc"),
        supports_parsing=True,
        capabilities=(
            "ast",
            "flowchart",
            "call_graph",
            "variable_flow",
            "complexity",
            "warnings",
            "diagnostics",
        ),
    )
    PYTHON = LanguageInfo(
        "python",
        "Python",
        (".py", ".pyw"),
        aliases=("py", "python3"),
        supports_parsing=False,
        capabilities=("detection", "diagnostics"),
    )
    JAVA = LanguageInfo(
        "java",
        "Java",
        (".java",),
        aliases=("java-lang",),
        supports_parsing=True,
        capabilities=(
            "ast",
            "flowchart",
            "call_graph",
            "variable_flow",
            "complexity",
            "warnings",
            "diagnostics",
        ),
    )
    JAVASCRIPT = LanguageInfo(
        "javascript",
        "JavaScript",
        (".js", ".mjs", ".cjs"),
        aliases=("js", "node"),
        supports_parsing=True,
        capabilities=(
            "ast",
            "flowchart",
            "call_graph",
            "variable_flow",
            "complexity",
            "warnings",
            "diagnostics",
        ),
    )
    TYPESCRIPT = LanguageInfo(
        "typescript",
        "TypeScript",
        (".ts", ".tsx"),
        aliases=("ts",),
        supports_parsing=True,
        capabilities=(
            "ast",
            "flowchart",
            "call_graph",
            "variable_flow",
            "complexity",
            "warnings",
            "diagnostics",
        ),
    )

    _ALL = (C, CPP, PYTHON, JAVA, JAVASCRIPT, TYPESCRIPT)

    @classmethod
    def resolve(
        cls, language: str | None = None, file_path: str | Path | None = None
    ) -> LanguageInfo | None:
        if language is not None:
            normalized = language.strip().lower().replace(" ", "")
            aliases = {"c++": "cpp", "cxx": "cpp", "cc": "cpp", "py": "python", "python3": "python", "js": "javascript", "ts": "typescript"}
            normalized = aliases.get(normalized, normalized)
            for info in cls._ALL:
                if normalized == info.language_id:
                    return info
                if normalized in {alias.lower().replace(" ", "") for alias in info.aliases}:
                    return info
            return None
        if file_path is None:
            return None
        extension = Path(file_path).suffix.lower()
        return next(
            (info for info in cls._ALL if extension in info.extensions),
            None,
        )
