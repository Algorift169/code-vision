from codevision.analysis import ASTAnalyzer, ASTExtractor
from codevision.parser import SourceParser


def test_ast_statistics_and_structural_extraction() -> None:
    source = """#include <stdio.h>
int global_value;
struct Item { int value; };
int sum(int count) {
    int total = 0;
    for (int i = 0; i < count; ++i) {
        if (i) total += i;
    }
    return total;
}
"""
    result = SourceParser().parse(source, language="c")
    statistics = ASTAnalyzer().statistics(result)
    facts = ASTExtractor().extract(result)

    assert statistics.total_nodes == result.node_count
    assert statistics.functions == 1
    assert statistics.variables >= 3
    assert statistics.loops == 1
    assert statistics.conditionals == 1
    assert statistics.max_nesting_depth == result.max_depth
    assert statistics.syntax_errors == 0
    assert facts.preprocessor
    assert facts.globals
    assert facts.structs
    assert facts.functions
    assert facts.parameters
    assert facts.locals
    assert facts.conditionals
    assert facts.loops
    assert facts.returns


def test_ast_statistics_count_syntax_errors() -> None:
    result = SourceParser().parse("int f( {", language="c")

    assert ASTAnalyzer().statistics(result).syntax_errors > 0
