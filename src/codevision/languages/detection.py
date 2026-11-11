from __future__ import annotations

from pathlib import Path

from .registry import LanguageRegistry


class LanguageDetector:
    """Detect the language of a path or a snippet without assuming a parser exists."""

    @staticmethod
    def detect(path: str | Path | None = None, source: str | None = None) -> object | None:
        candidate_path = Path(path) if path is not None else None
        if candidate_path is not None:
            adapter = LanguageRegistry.resolve(file_path=candidate_path)
            if adapter is not None:
                return adapter

        if source is not None:
            normalized = source.strip()
            if not normalized:
                return None
            if any(token in normalized for token in ("def ", "import ", "from ", "class ")):
                return LanguageRegistry.resolve("python")
            if "=>" in normalized or "const " in normalized or "export default" in normalized:
                return LanguageRegistry.resolve("javascript")
            if "public class " in normalized or "package " in normalized:
                return LanguageRegistry.resolve("java")
            if "<typename" in normalized or "namespace " in normalized:
                return LanguageRegistry.resolve("cpp")
            if "#include" in normalized or "int main" in normalized:
                return LanguageRegistry.resolve("c")

        return None


def detect_language(path: str | Path | None = None, source: str | None = None):
    return LanguageDetector.detect(path=path, source=source)
