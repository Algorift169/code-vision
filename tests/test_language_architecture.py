from pathlib import Path

from codevision.languages import LanguageRegistry, detect_language
from codevision.parser import LanguageRegistry as ParserRegistry


def test_language_registry_recognizes_supported_languages() -> None:
    assert ParserRegistry.resolve(file_path="main.c").language_id == "c"
    assert ParserRegistry.resolve(file_path="main.py").language_id == "python"
    assert ParserRegistry.resolve(file_path="client.ts").language_id == "typescript"
    assert ParserRegistry.resolve(file_path="app.js").language_id == "javascript"
    assert ParserRegistry.resolve(language="C++").language_id == "cpp"


def test_language_detection_reports_capabilities_without_overpromising() -> None:
    detected = detect_language(Path("module.py"))
    assert detected.language_id == "python"
    assert detected.supports_parsing is False
    assert detected.capabilities

    adapter = LanguageRegistry.resolve("python")
    assert adapter is not None
    assert adapter.language_id == "python"
    assert adapter.display_name == "Python"
    assert adapter.supports_parsing is False
