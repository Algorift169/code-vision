from __future__ import annotations

from dataclasses import dataclass

from ..model import ASTNode, ASTResult
from .ast_extractor import ASTExtractor


@dataclass(frozen=True, slots=True)
class ASTStatistics:
    total_nodes: int
    functions: int
    variables: int
    loops: int
    conditionals: int
    function_calls: int
    declarations: int
    max_nesting_depth: int
    syntax_errors: int


class ASTAnalyzer:
    """Extract structural facts and statistics from a normalized AST."""

    _FUNCTIONS = {"function_definition", "function_declaration"}
    _VARIABLES = {
        "declaration",
        "parameter_declaration",
        "init_declarator",
        "field_declaration",
        "field_declarator",
    }
    _LOOPS = {"for_statement", "while_statement", "do_statement", "for_range_loop"}
    _CONDITIONALS = {"if_statement", "switch_statement", "conditional_expression"}
    _DECLARATIONS = {
        "declaration",
        "field_declaration",
        "type_definition",
        "struct_specifier",
        "union_specifier",
        "enum_specifier",
        "class_specifier",
        "namespace_definition",
        "function_definition",
        "function_declaration",
    }

    def statistics(self, result: ASTResult) -> ASTStatistics:
        nodes = tuple(result.root.walk())
        depth_by_id: dict[str, int] = {}
        max_depth = 0
        for node in nodes:
            depth = 1 if node.parent_id is None else depth_by_id[node.parent_id] + 1
            depth_by_id[node.node_id] = depth
            max_depth = max(max_depth, depth)
        function_declarations = len(ASTExtractor._function_declaration_ids(nodes))
        return ASTStatistics(
            total_nodes=len(nodes),
            functions=sum(node.node_type in self._FUNCTIONS for node in nodes)
            + function_declarations,
            variables=sum(
                node.node_type in self._VARIABLES
                and (
                    node.node_type != "declaration"
                    and node.node_type != "field_declaration"
                    or not any(
                        child.node_type
                        in {"init_declarator", "field_declarator"}
                        for child in node.children
                    )
                )
                for node in nodes
            ),
            loops=sum(node.node_type in self._LOOPS for node in nodes),
            conditionals=sum(node.node_type in self._CONDITIONALS for node in nodes),
            function_calls=sum(node.node_type == "call_expression" for node in nodes),
            declarations=sum(node.node_type in self._DECLARATIONS for node in nodes),
            max_nesting_depth=max_depth,
            syntax_errors=result.syntax_error_count,
        )

    def extract(self, result: ASTResult, node_type: str) -> tuple[ASTNode, ...]:
        return tuple(node for node in result.root.walk() if node.node_type == node_type)
