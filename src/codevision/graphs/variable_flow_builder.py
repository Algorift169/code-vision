from __future__ import annotations

from typing import ClassVar

from ..analysis.variable_flow import VariableFlowAnalysis
from ..model import ASTNode, ASTResult
from .variable_flow import VariableFlowEdge, VariableFlowGraph, VariableFlowNode


class VariableFlowBuilder:
    """Build a compact variable-flow graph from actual assignments and reads."""

    _DECLARATION_TYPES: ClassVar[set[str]] = {
        "declaration",
        "assignment",
        "assignment_expression",
        "init_declarator",
        "variable_declaration",
        "lexical_declaration",
        "parameter",
    }
    _ASSIGNMENT_TYPES: ClassVar[set[str]] = {
        "assignment",
        "assignment_expression",
        "augmented_assignment",
    }
    _IDENTIFIER_TYPES: ClassVar[set[str]] = {"identifier", "name", "field_identifier"}

    @classmethod
    def _assignment_target_name(cls, node: ASTNode) -> str | None:
        if node.node_type in cls._ASSIGNMENT_TYPES:
            for child in node.children:
                if child.node_type in cls._IDENTIFIER_TYPES:
                    return child.source_text.strip()
        if node.node_type in {"declaration", "init_declarator", "variable_declaration", "parameter"}:
            for child in node.children:
                if child.node_type in cls._IDENTIFIER_TYPES:
                    return child.source_text.strip()
        return None

    @classmethod
    def _is_assignment_target(cls, node: ASTNode, target_name: str) -> bool:
        if node.node_type in cls._ASSIGNMENT_TYPES or node.node_type in {"declaration", "init_declarator", "variable_declaration", "parameter"}:
            return cls._assignment_target_name(node) == target_name
        return False

    @classmethod
    def _is_read_identifier(cls, node: ASTNode, target_name: str, nodes_by_id: dict[str, ASTNode]) -> bool:
        if node.node_type not in cls._IDENTIFIER_TYPES:
            return False
        if node.source_text.strip() != target_name:
            return False
        parent = nodes_by_id.get(node.parent_id) if node.parent_id is not None else None
        if parent is not None and parent.node_type == "call" and parent.children and parent.children[0].node_id == node.node_id:
            return False
        if parent is not None and parent.node_type in cls._ASSIGNMENT_TYPES:
            if any(child.node_id == node.node_id for child in parent.children):
                return False
        return True

    def build(self, result: ASTResult, variable_name: str, scope: str | None = None) -> VariableFlowGraph:
        analysis = VariableFlowAnalysis(source_file=result.file_path, language=result.language).analyze(result)
        facts = [fact for fact in analysis.facts if fact.name == variable_name and (scope is None or fact.scope == scope)]
        graph = VariableFlowGraph(
            source_file=result.file_path,
            language=result.language,
            variable_name=variable_name,
            scope=scope or (facts[0].scope if facts else "module"),
            symbol_id=f"{result.file_path or 'source'}:{variable_name}:{scope or 'module'}",
            nodes=[],
            edges=[],
        )

        if not facts:
            return graph

        fact = facts[0]
        definitions = fact.definitions if fact.definitions else ((fact.declaration,) if fact.declaration else ())
        definition_nodes: list[VariableFlowNode] = []
        last_definition_node: VariableFlowNode | None = None
        for index, definition in enumerate(definitions):
            label = "initialization" if index == 0 else "assignment"
            def_node = VariableFlowNode(
                node_id=f"df-{graph.variable_name}-{index}",
                symbol_id=f"{graph.symbol_id}:def:{index}",
                name=variable_name,
                scope=fact.scope,
                kind=label,
                source_node=definition.source_node,
                metadata={
                    "source_line": str(definition.line or 0),
                    "expression": definition.expression,
                },
            )
            graph.nodes.append(def_node)
            assignment_node = VariableFlowNode(
                node_id=f"assign-{graph.variable_name}-{index}",
                symbol_id=f"{graph.symbol_id}:assign:{index}",
                name=variable_name,
                scope=fact.scope,
                kind="assignment",
                source_node=definition.source_node,
                metadata={
                    "source_line": str(definition.line or 0),
                    "expression": definition.expression,
                },
            )
            graph.nodes.append(assignment_node)
            graph.edges.append(
                VariableFlowEdge(
                    edge_id=f"e-{len(graph.edges)}",
                    source_id=def_node.node_id,
                    target_id=assignment_node.node_id,
                    edge_type="assignment",
                    label="flow",
                    source_node=def_node.source_node,
                    target_node=assignment_node.source_node,
                )
            )
            definition_nodes.append(assignment_node)
            last_definition_node = assignment_node

        if len(definition_nodes) > 1:
            merge = VariableFlowNode(
                node_id=f"merge-{graph.variable_name}",
                symbol_id=f"{graph.symbol_id}:merge",
                name=variable_name,
                scope=fact.scope,
                kind="merge",
                source_node=definition_nodes[-1].source_node,
                metadata={"source_line": str(definition_nodes[-1].metadata.get('source_line', '0'))},
            )
            graph.nodes.append(merge)
            for node in definition_nodes:
                graph.edges.append(
                    VariableFlowEdge(
                        edge_id=f"e-{len(graph.edges)}",
                        source_id=node.node_id,
                        target_id=merge.node_id,
                        edge_type="merge",
                        label="merge",
                        source_node=node.source_node,
                        target_node=merge.source_node,
                    )
                )
            last_definition_node = merge

        if not definition_nodes:
            last_definition_node = None

        for index, use in enumerate(fact.uses):
            use_node = VariableFlowNode(
                node_id=f"use-{graph.variable_name}-{index}",
                symbol_id=f"{graph.symbol_id}:use:{index}",
                name=variable_name,
                scope=fact.scope,
                kind="usage",
                source_node=use.source_node,
                metadata={
                    "source_line": str(use.line or 0),
                    "expression": use.source_node.source_text if use.source_node else "",
                },
            )
            graph.nodes.append(use_node)
            if last_definition_node is not None:
                graph.edges.append(
                    VariableFlowEdge(
                        edge_id=f"e-{len(graph.edges)}",
                        source_id=last_definition_node.node_id,
                        target_id=use_node.node_id,
                        edge_type="read",
                        label="use",
                        source_node=last_definition_node.source_node,
                        target_node=use_node.source_node,
                    )
                )
            last_definition_node = use_node

        for index, node in enumerate(graph.nodes):
            node.x = 30 + (index % 2) * 260
            node.y = 30 + (index // 2) * 110
            node.width = 210
            node.height = 70

        return graph


__all__ = ["VariableFlowBuilder"]
