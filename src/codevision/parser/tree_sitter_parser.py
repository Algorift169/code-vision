from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter


@dataclass(frozen=True, slots=True)
class NativeParseResult:
    tree: object
    duration_ms: float


class TreeSitterParser:
    """Create Tree-sitter parsers for supported C-family grammars."""

    @staticmethod
    def parse(source: bytes, language_id: str) -> NativeParseResult:
        try:
            from tree_sitter import Language, Parser
            import tree_sitter_c
            import tree_sitter_cpp
        except ImportError as error:
            raise RuntimeError(
                "Tree-sitter C/C++ parser dependencies are unavailable"
            ) from error

        grammar_factory = {
            "c": tree_sitter_c.language,
            "cpp": tree_sitter_cpp.language,
        }.get(language_id)
        if grammar_factory is None:
            raise ValueError(f"Unsupported parser language: {language_id}")

        try:
            language = Language(grammar_factory())
            try:
                parser = Parser(language)
            except TypeError:
                parser = Parser()
                parser.language = language
        except (TypeError, ValueError, RuntimeError) as error:
            raise RuntimeError(
                f"Could not initialize the Tree-sitter {language_id} parser: {error}"
            ) from error

        started = perf_counter()
        try:
            tree = parser.parse(source)
        except (TypeError, ValueError, RuntimeError) as error:
            raise RuntimeError(f"Tree-sitter parsing failed: {error}") from error
        return NativeParseResult(
            tree=tree,
            duration_ms=(perf_counter() - started) * 1000,
        )
