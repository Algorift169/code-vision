from __future__ import annotations

from pathlib import Path

from .base import LanguageAdapter


class LanguageRegistry:
    """Central registry for identifiable source languages and their capabilities."""

    _ADAPTERS: tuple[LanguageAdapter, ...] = (
        LanguageAdapter(
            language_id="c",
            display_name="C",
            extensions=(".c", ".h"),
            aliases=("c-lang",),
            supports_parsing=True,
            capabilities=("ast", "flowchart", "call_graph", "variable_flow", "complexity", "warnings", "diagnostics"),
            description="The native C parser used by the existing analyzer pipeline.",
        ),
        LanguageAdapter(
            language_id="cpp",
            display_name="C++",
            extensions=(".cpp", ".cc", ".cxx", ".hpp", ".hh", ".hxx"),
            aliases=("c++", "cxx", "cc"),
            supports_parsing=True,
            capabilities=("ast", "flowchart", "call_graph", "variable_flow", "complexity", "warnings", "diagnostics"),
            description="The native C++ parser used by the existing analyzer pipeline.",
        ),
        LanguageAdapter(
            language_id="python",
            display_name="Python",
            extensions=(".py", ".pyw"),
            aliases=("py", "python3"),
            supports_parsing=False,
            capabilities=("detection", "diagnostics"),
            description="Detected and recognized for future Python analysis; parsing is intentionally unsupported until a Python adapter is implemented.",
        ),
        LanguageAdapter(
            language_id="java",
            display_name="Java",
            extensions=(".java",),
            aliases=("java-lang",),
            supports_parsing=False,
            capabilities=("detection", "diagnostics"),
            description="Java support is planned behind the common adapter interface.",
        ),
        LanguageAdapter(
            language_id="javascript",
            display_name="JavaScript",
            extensions=(".js", ".mjs", ".cjs"),
            aliases=("js", "node"),
            supports_parsing=False,
            capabilities=("detection", "diagnostics"),
            description="JavaScript detection is available; parsing remains to be implemented.",
        ),
        LanguageAdapter(
            language_id="typescript",
            display_name="TypeScript",
            extensions=(".ts", ".tsx"),
            aliases=("ts",),
            supports_parsing=False,
            capabilities=("detection", "diagnostics"),
            description="TypeScript detection is available; parsing remains to be implemented.",
        ),
        LanguageAdapter(
            language_id="csharp",
            display_name="C#",
            extensions=(".cs",),
            aliases=("c#", "c-sharp"),
            supports_parsing=False,
            capabilities=("detection", "diagnostics"),
            description="C# is recognized by the registry but intentionally not parsed yet.",
        ),
        LanguageAdapter(
            language_id="go",
            display_name="Go",
            extensions=(".go",),
            aliases=("golang",),
            supports_parsing=False,
            capabilities=("detection", "diagnostics"),
            description="Go support is future-facing and intentionally isolated behind the adapter interface.",
        ),
        LanguageAdapter(
            language_id="rust",
            display_name="Rust",
            extensions=(".rs",),
            aliases=("rust-lang",),
            supports_parsing=False,
            capabilities=("detection", "diagnostics"),
            description="Rust is registered for language detection and future adapter support.",
        ),
        LanguageAdapter(
            language_id="php",
            display_name="PHP",
            extensions=(".php",),
            aliases=("php-lang",),
            supports_parsing=False,
            capabilities=("detection", "diagnostics"),
            description="PHP is recognized by path-based detection while the parser remains opt-in.",
        ),
        LanguageAdapter(
            language_id="ruby",
            display_name="Ruby",
            extensions=(".rb",),
            aliases=("rb",),
            supports_parsing=False,
            capabilities=("detection", "diagnostics"),
            description="Ruby support is reserved for a dedicated later adapter.",
        ),
        LanguageAdapter(
            language_id="kotlin",
            display_name="Kotlin",
            extensions=(".kt", ".kts"),
            aliases=("kt",),
            supports_parsing=False,
            capabilities=("detection", "diagnostics"),
            description="Kotlin is in the planned registry but not yet parsed.",
        ),
        LanguageAdapter(
            language_id="swift",
            display_name="Swift",
            extensions=(".swift",),
            aliases=("swift-lang",),
            supports_parsing=False,
            capabilities=("detection", "diagnostics"),
            description="Swift is recognized for future architecture support.",
        ),
        LanguageAdapter(
            language_id="dart",
            display_name="Dart",
            extensions=(".dart",),
            aliases=("dart-lang",),
            supports_parsing=False,
            capabilities=("detection", "diagnostics"),
            description="Dart is part of the planned multi-language registry.",
        ),
        LanguageAdapter(
            language_id="sql",
            display_name="SQL",
            extensions=(".sql",),
            aliases=("sql-lang",),
            supports_parsing=False,
            capabilities=("detection", "diagnostics"),
            description="SQL is recognized as a future adapter target.",
        ),
    )

    @classmethod
    def all(cls) -> tuple[LanguageAdapter, ...]:
        return cls._ADAPTERS

    @classmethod
    def resolve(
        cls,
        language: str | None = None,
        file_path: str | Path | None = None,
    ) -> LanguageAdapter | None:
        if language is not None:
            normalized = language.strip().lower().replace(" ", "")
            alias_map = {
                "c++": "cpp",
                "cxx": "cpp",
                "cc": "cpp",
                "py": "python",
                "python3": "python",
                "js": "javascript",
                "ts": "typescript",
                "c#": "csharp",
                "csharp": "csharp",
                "c-sharp": "csharp",
                "golang": "go",
                "rust-lang": "rust",
                "php-lang": "php",
                "rb": "ruby",
                "kotlin": "kotlin",
                "swift-lang": "swift",
                "dart-lang": "dart",
                "sql-lang": "sql",
            }
            normalized = alias_map.get(normalized, normalized)
            for adapter in cls._ADAPTERS:
                if adapter.language_id == normalized or normalized in {
                    alias.lower().replace(" ", "") for alias in adapter.aliases
                }:
                    return adapter
            return None

        if file_path is None:
            return None

        extension = Path(file_path).suffix.lower()
        for adapter in cls._ADAPTERS:
            if extension in {item.lower() for item in adapter.extensions}:
                return adapter
        return None
