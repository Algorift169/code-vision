from codevision.complexity import ComplexityAnalyzer


def test_complexity_analyzer_detects_branching_and_looping() -> None:
    source = """
def sample(items):
    total = 0
    if items is None:
        return 0
    for item in items:
        total += item
    return total
"""
    report = ComplexityAnalyzer().analyze(source, file_path="sample.py", language="python")

    assert report.functions
    function = report.functions[0]
    assert function.cyclomatic >= 2
    assert function.cognitive >= 2
    assert function.time_complexity in {"O(n)", "O(n²)", "O(1)"}
    assert function.space_complexity in {"O(1)", "O(n)"}


def test_complexity_analyzer_detects_nested_loops() -> None:
    source = """
def matrix(items):
    for x in items:
        for y in items:
            if x == y:
                return True
    return False
"""
    report = ComplexityAnalyzer().analyze(source, file_path="matrix.py", language="python")

    function = report.functions[0]
    assert function.cyclomatic >= 3
    assert function.time_complexity == "O(n²)"
    assert function.risk in {"moderate", "high"}
