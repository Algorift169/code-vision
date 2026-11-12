from __future__ import annotations

from typing import ClassVar

from ..model import ASTNode, ASTResult
from .call_graph import CallGraph, CallGraphEdge, CallGraphNode


class CallGraphBuilder:
    """Build caller-to-callee edges between functions defined in one AST."""

    _FUNCTION_TYPES: ClassVar[set[str]] = {
        "function_definition",
        "function_declaration",
        "method_declaration",
        "method_definition",
        "constructor_declaration",
    }
    _CALL_TYPES: ClassVar[set[str]] = {"call", "call_expression", "method_invocation"}
    _ARGUMENT_TYPES: ClassVar[set[str]] = {"argument_list", "arguments", "value_arguments"}
    _NAME_TYPES: ClassVar[set[str]] = {
        "identifier",
        "field_identifier",
        "property_identifier",
        "type_identifier",
    }

    def build(self, result: ASTResult) -> CallGraph:
        graph = CallGraph(source_file=result.file_path, language=result.language)
        function_nodes = [
            node for node in result.root.walk()
            if node.node_type in self._FUNCTION_TYPES
        ]
        functions_by_name: dict[str, list[CallGraphNode]] = {}
        for ast_node in function_nodes:
            name = self._function_name(ast_node)
            graph_node = CallGraphNode(
                node_id=f"function-{ast_node.node_id}",
                name=name,
                source_node=ast_node,
            )
            graph.nodes.append(graph_node)
            functions_by_name.setdefault(name, []).append(graph_node)

        edges: dict[tuple[str, str], CallGraphEdge] = {}
        for caller in graph.nodes:
            for call in self._calls_in(caller.source_node):
                callee_name = self._callee_name(call)
                candidates = functions_by_name.get(callee_name, [])
                if len(candidates) != 1:
                    continue
                callee = candidates[0]
                key = (caller.node_id, callee.node_id)
                edge = edges.setdefault(
                    key, CallGraphEdge(source_id=caller.node_id, target_id=callee.node_id)
                )
                edge.call_sites.append(call)
        graph.edges.extend(edges.values())
        return graph

    @classmethod
    def _function_name(cls, function: ASTNode) -> str:
        for node in function.walk():
            if node.node_type in cls._NAME_TYPES:
                return node.source_text.strip()
        return function.display_name

    @classmethod
    def _callee_name(cls, call: ASTNode) -> str:
        callable_parts: list[ASTNode] = []
        for child in call.children:
            if child.node_type in cls._ARGUMENT_TYPES:
                break
            callable_parts.append(child)
        names = [
            node.source_text.strip()
            for part in callable_parts
            for node in part.walk()
            if node.node_type in cls._NAME_TYPES
        ]
        return names[-1] if names else ""

    @classmethod
    def _calls_in(cls, function: ASTNode) -> list[ASTNode]:
        calls: list[ASTNode] = []
        stack = list(reversed(function.children))
        while stack:
            node = stack.pop()
            if node.node_type in cls._FUNCTION_TYPES:
                continue
            if node.node_type in cls._CALL_TYPES:
                calls.append(node)
            stack.extend(reversed(node.children))
        return calls


__all__ = ["CallGraphBuilder"]