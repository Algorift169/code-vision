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
        nodes_by_id = {node.node_id: node for node in result.root.walk()}
        functions_by_name: dict[str, list[CallGraphNode]] = {}
        simple_name_map: dict[str, list[CallGraphNode]] = {}
        for ast_node in function_nodes:
            name = self._function_name(ast_node)
            qualified_name = self._qualified_name(ast_node, nodes_by_id)
            graph_node = CallGraphNode(
                node_id=f"function-{ast_node.node_id}",
                name=name,
                qualified_name=qualified_name,
                source_node=ast_node,
            )
            graph.nodes.append(graph_node)
            functions_by_name.setdefault(qualified_name, []).append(graph_node)
            simple_name_map.setdefault(name, []).append(graph_node)

        edges: dict[tuple[str, str], CallGraphEdge] = {}
        for caller in graph.nodes:
            for call in self._calls_in(caller.source_node):
                callee_name = self._callee_name(call)
                if not callee_name:
                    continue
                target = self._resolve_target(caller.qualified_name, callee_name, functions_by_name, simple_name_map)
                if target is None:
                    continue
                candidates = functions_by_name.get(target, [])
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
    def _qualified_name(cls, function: ASTNode, nodes_by_id: dict[str, ASTNode]) -> str:
        names: list[str] = []
        current_id = function.node_id
        while current_id is not None:
            current = nodes_by_id.get(current_id)
            if current is None:
                break
            if current.node_type in cls._FUNCTION_TYPES:
                name = cls._function_name(current)
                if name:
                    names.append(name)
            elif current.node_type in {"class_definition", "class_declaration", "class_specifier"}:
                for node in current.walk():
                    if node.node_type in {"identifier", "name"}:
                        names.append(node.source_text.strip())
                        break
            current_id = current.parent_id
        names.reverse()
        return ".".join(names)

    @classmethod
    def _resolve_target(
        cls,
        caller_qname: str,
        callee_name: str,
        functions_by_name: dict[str, list[CallGraphNode]],
        simple_name_map: dict[str, list[CallGraphNode]],
    ) -> str | None:
        scope = caller_qname.rsplit(".", 1)[0] if "." in caller_qname else ""
        candidates = [
            f"{scope}.{callee_name}" if scope else None,
            callee_name,
        ]
        for candidate in candidates:
            if candidate is None:
                continue
            matches = functions_by_name.get(candidate, [])
            if len(matches) == 1:
                return candidate

        if scope:
            scoped = [
                node.qualified_name
                for node in simple_name_map.get(callee_name, [])
                if node.qualified_name.startswith(f"{scope}.")
            ]
            if len(scoped) == 1:
                return scoped[0]

        matches = simple_name_map.get(callee_name, [])
        if len(matches) == 1:
            return matches[0].qualified_name
        return None

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
    def _calls_in(cls, function: ASTNode | None) -> list[ASTNode]:
        if function is None:
            return []
        calls: list[ASTNode] = []

        def walk(node: ASTNode) -> None:
            for child in node.children:
                if child.node_type in cls._FUNCTION_TYPES:
                    continue
                if child.node_type in cls._CALL_TYPES:
                    calls.append(child)
                walk(child)

        walk(function)
        return calls


__all__ = ["CallGraphBuilder"]