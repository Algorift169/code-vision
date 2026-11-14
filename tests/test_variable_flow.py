from codevision.analysis.variable_flow import VariableFlowAnalysis
from codevision.graphs import VariableFlowBuilder
from codevision.parser import SourceParser
from codevision.ui.analysis_panel import AnalysisPanel


def test_variable_flow_tracks_definition_to_use() -> None:
    source = """
value = 10
result = value + 1
print(result)
"""
    result = SourceParser().parse(source, language="python")

    graph = VariableFlowBuilder().build(result, "value")

    assert graph.variable_name == "value"
    assert graph.edges
    assert any(edge.edge_type == "assignment" for edge in graph.edges)
    assert any(edge.edge_type == "read" for edge in graph.edges)


def test_variable_flow_analysis_collects_scoped_facts() -> None:
    source = """
def calculate_price(price, quantity):
    subtotal = price * quantity
    discount = 10
    if subtotal > 100:
        discount = 20
    return subtotal - discount

price = 50
quantity = 3
result = calculate_price(price, quantity)
"""
    result = SourceParser().parse(source, language="python")
    analysis = VariableFlowAnalysis(source_file=None, language=result.language).analyze(result)

    assert any(fact.name == "discount" and fact.scope == "calculate_price" for fact in analysis.facts)
    assert any(fact.name == "price" and fact.scope == "module" for fact in analysis.facts)
    assert any(len(fact.definitions) >= 1 for fact in analysis.facts)
    assert any(len(fact.uses) >= 1 for fact in analysis.facts)


def test_variable_flow_builder_keeps_distinct_scope_entries() -> None:
    source = """
value = 1

def sample():
    value = 2
    return value
"""
    result = SourceParser().parse(source, language="python")

    module_graph = VariableFlowBuilder().build(result, "value")
    func_graph = VariableFlowBuilder().build(result, "value", scope="sample")

    assert module_graph.scope == "module"
    assert func_graph.scope == "sample"
    assert module_graph.variable_name == "value"
    assert func_graph.variable_name == "value"


def test_analysis_panel_var_flow_builds_graph_for_real_source_file(tmp_path) -> None:
    panel = AnalysisPanel()
    var_flow = panel._section_placeholders["Var Flow"]

    source = "int value = 1; int result = value + 2;"
    panel.set_source(source, tmp_path / "sample.c", "c")

    assert var_flow._graph is not None
    assert var_flow._graph.variable_name in {"value", "result"}
    assert len(var_flow._graph.nodes) >= 2
    assert len(var_flow._graph.edges) >= 1
