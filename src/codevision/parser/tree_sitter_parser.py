from __future__ import annotations

from importlib import import_module
from dataclasses import dataclass
from time import perf_counter


@dataclass(frozen=True, slots=True)
class NativeParseResult:
    tree: object
    duration_ms: float


class TreeSitterParser:
    """Create Tree-sitter parsers for the supported language grammars."""

    @staticmethod
    def parse(source: bytes, language_id: str) -> NativeParseResult:
        try:
            from tree_sitter import Language, Parser
        except ImportError as error:
            raise RuntimeError(
                "Tree-sitter is unavailable; install the parser dependencies"
            ) from error

        grammar = {
            "c": ("tree_sitter_c", "language"),
            "cpp": ("tree_sitter_cpp", "language"),
            "css": ("tree_sitter_css", "language"),
            "java": ("tree_sitter_java", "language"),
            "javascript": ("tree_sitter_javascript", "language"),
            "python": ("tree_sitter_python", "language"),
            "typescript": ("tree_sitter_typescript", "language_typescript"),
            "tsx": ("tree_sitter_typescript", "language_tsx"),
        }.get(language_id)
        if grammar is None:
            raise ValueError(f"Unsupported parser language: {language_id}")
        module_name, factory_name = grammar
        try:
            grammar_factory = getattr(import_module(module_name), factory_name)
        except (ImportError, AttributeError) as error:
            raise RuntimeError(
                f"The Tree-sitter grammar for {language_id} is unavailable"
            ) from error

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
