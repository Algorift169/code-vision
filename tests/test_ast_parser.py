from pathlib import Path

import pytest

from codevision.parser import LanguageRegistry, SourceParser


def test_language_registry_maps_supported_extensions() -> None:
    assert LanguageRegistry.resolve(file_path="main.c").language_id == "c"
    assert LanguageRegistry.resolve(file_path="header.h").language_id == "c"
    for extension in (".cpp", ".cc", ".cxx", ".hpp", ".hh", ".hxx"):
        assert (
            LanguageRegistry.resolve(file_path=f"unit{extension}").language_id
            == "cpp"
        )
    assert LanguageRegistry.resolve(file_path="Main.java").language_id == "java"
    assert LanguageRegistry.resolve(file_path="main.py").language_id == "python"
    assert LanguageRegistry.resolve(file_path="theme.css").language_id == "css"
    assert LanguageRegistry.resolve(file_path="client.ts").language_id == "typescript"


def test_parser_normalizes_valid_c_structure(tmp_path: Path) -> None:
    source = """#include <stdio.h>
struct Point { int x; int y; };
enum Mode { FAST, SAFE };
int total;
int sum(int n) {
    int result = 0;
    for (int i = 0; i < n; ++i) {
        if (i > 0) result += i;
    }
    return result;
}
"""
    result = SourceParser().parse(source, file_path=tmp_path / "main.c")
    nodes = tuple(result.root.walk())
    node_types = {node.node_type for node in nodes}

    assert result.succeeded
    assert result.language == "c"
    assert result.file_path == (tmp_path / "main.c").resolve()
    assert {
        "translation_unit",
        "preproc_include",
        "struct_specifier",
        "enum_specifier",
        "function_definition",
        "for_statement",
        "if_statement",
        "return_statement",
    } <= node_types
    assert result.node_count == len(nodes)
    assert result.max_depth > 1
    function = next(node for node in nodes if node.node_type == "function_definition")
    assert function.display_name.startswith("Function Definition:")


def test_parser_supports_cpp_namespaces_classes_and_templates() -> None:
    source = """namespace sample {
template <typename T>
class Box {
public:
    T value;
    T get() { return value; }
};
}
"""
    result = SourceParser().parse(source, language="cpp")
    node_types = {node.node_type for node in result.root.walk()}

    assert result.succeeded
    assert result.language == "cpp"
    assert {
        "namespace_definition",
        "template_declaration",
        "class_specifier",
        "function_definition",
    } <= node_types


def test_parser_supports_java_classes_and_methods() -> None:
    source = """public class Sample {
    private int value;

    public int getValue() {
        return value;
    }
}
"""
    result = SourceParser().parse(source, language="java")
    node_types = {node.node_type for node in result.root.walk()}

    assert result.succeeded
    assert result.language == "java"
    assert {"class_declaration", "method_declaration", "return_statement"} <= node_types


def test_parser_supports_python_functions_and_classes(tmp_path: Path) -> None:
    source = """class Counter:
    def increment(self, amount):
        value = amount + 1
        return value
"""
    result = SourceParser().parse(source, file_path=tmp_path / "counter.py")
    node_types = {node.node_type for node in result.root.walk()}

    assert result.succeeded
    assert result.language == "python"
    assert {"class_definition", "function_definition", "return_statement"} <= node_types


def test_parser_supports_css_rules_and_declarations(tmp_path: Path) -> None:
    source = """.panel { color: red; margin: 0 auto; }
@media (min-width: 40rem) { .panel { display: grid; } }
"""
    result = SourceParser().parse(source, file_path=tmp_path / "theme.css")
    node_types = {node.node_type for node in result.root.walk()}

    assert result.succeeded
    assert result.language == "css"
    assert {"stylesheet", "rule_set", "declaration"} <= node_types


def test_parser_accepts_empty_source_as_empty_translation_unit() -> None:
    result = SourceParser().parse("", language="c")

    assert result.succeeded
    assert result.root.node_type == "translation_unit"
    assert result.node_count == 1


def test_parser_retains_malformed_syntax_as_partial_result() -> None:
    result = SourceParser().parse("int main( { return 0;", language="c")

    assert result.is_partial
    assert result.syntax_error_count > 0
    assert result.errors
    assert any(node.has_error or node.is_missing for node in result.root.walk())


def test_parser_rejects_unsupported_language_and_source_type() -> None:
    parser = SourceParser()

    with pytest.raises(ValueError, match="does not support"):
        parser.parse("int main() {}", language="rust")
    with pytest.raises(TypeError, match="must be str or bytes"):
        parser.parse(123, language="c")
