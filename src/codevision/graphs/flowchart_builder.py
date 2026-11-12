from __future__ import annotations

from typing import ClassVar

from ..model import ASTNode, ASTResult
from .flowchart_ir import (
    FlowchartEdge,
    FlowchartGraph,
    FlowchartNode,
    FlowchartNodeKind,
)


class FlowchartBuilder:
    """Translate supported AST statements into language-independent graphs."""

    _FUNCTION_TYPES: ClassVar[set[str]] = {
        "function_definition",
        "function_declaration",
        "method_declaration",
        "method_definition",
        "constructor_declaration",
    }
    _BLOCK_TYPES: ClassVar[set[str]] = {
        "block",
        "compound_statement",
        "statement_block",
        "program",
        "module",
        "translation_unit",
    }
    _IF_TYPES: ClassVar[set[str]] = {"if_statement"}
    _ELSE_TYPES: ClassVar[set[str]] = {"else_clause", "elif_clause", "else_if_clause"}
    _LOOP_TYPES: ClassVar[set[str]] = {
        "for_statement",
        "for_in_statement",
        "enhanced_for_statement",
        "while_statement",
    }
    _CALL_TYPES: ClassVar[set[str]] = {"call", "call_expression"}
    _RETURN_TYPES: ClassVar[set[str]] = {"return_statement"}
    _BREAK_TYPES: ClassVar[set[str]] = {"break_statement"}
    _CONTINUE_TYPES: ClassVar[set[str]] = {"continue_statement"}
    _THROW_TYPES: ClassVar[set[str]] = {"throw_statement", "raise_statement"}
    _ATOMIC_TYPES: ClassVar[set[str]] = {
        "declaration",
        "lexical_declaration",
        "variable_declaration",
        "local_variable_declaration",
        "expression_statement",
        "assignment",
        "assignment_expression",
        "augmented_assignment",
        "update_expression",
        "call",
        "call_expression",
        "pass_statement",
        "empty_statement",
        "assert_statement",
        "delete_expression",
        "yield_statement",
    }
    _OUTPUT_CALLS: ClassVar[set[str]] = {
        "print",
        "printf",
        "fprintf",
        "puts",
        "putchar",
        "println",
        "write",
        "writeln",
        "log",
    }
    _INPUT_CALLS: ClassVar[set[str]] = {
        "input",
        "scanf",
        "fscanf",
        "gets",
        "fgets",
        "read",
        "readline",
    }

    def build(
        self,
        result: ASTResult,
        source: str | bytes | None = None,
    ) -> FlowchartGraph:
        functions = self._functions(result.root)
        selected = next(
            (node for node in functions if self._function_name(node) == "main"),
            functions[0] if functions else None,
        )
        return self._build_scope(result, source, selected)

    def build_all(
        self,
        result: ASTResult,
        source: str | bytes | None = None,
    ) -> list[FlowchartGraph]:
        """Build one graph per discovered function, or one top-level graph."""
        functions = self._functions(result.root)
        if not functions:
            return [self._build_scope(result, source, None)]
        return [self._build_scope(result, source, function) for function in functions]

    @classmethod
    def _functions(cls, root: ASTNode) -> list[ASTNode]:
        return [node for node in root.walk() if node.node_type in cls._FUNCTION_TYPES]

    @classmethod
    def _function_name(cls, function: ASTNode) -> str:
        for node in function.walk():
            if node.node_type in {"identifier", "name", "type_identifier"}:
                return node.source_text.strip()
        return "function"

    @classmethod
    def _function_body(cls, function: ASTNode) -> list[ASTNode]:
        for child in reversed(function.children):
            if child.node_type in cls._BLOCK_TYPES:
                return child.children
        return []

    def _build_scope(
        self,
        result: ASTResult,
        source: str | bytes | None,
        function: ASTNode | None,
    ) -> FlowchartGraph:
        source_bytes = (
            source.encode("utf-8") if isinstance(source, str) else source
        )

        def exact_source(node: ASTNode) -> str:
            if source_bytes is None:
                return node.source_text.strip()
            return source_bytes[
                node.location.start_byte : node.location.end_byte
            ].decode("utf-8", errors="replace").strip()

        function_name = self._function_name(function) if function is not None else None
        function_nodes = self._functions(result.root)
        graph = FlowchartGraph(
            graph_id=(
                f"flowchart-{result.file_path.name if result.file_path else 'source'}"
                f"-{function_name}"
                if function_name
                else f"flowchart-{result.file_path.name if result.file_path else 'source'}"
            ),
            source_file=result.file_path,
            language=result.language,
            function_name=function_name,
            nodes=[],
            edges=[],
            entry=None,
            exit_nodes=[],
            metadata={
                "node_count": 0,
                "functions": [
                    {
                        "name": self._function_name(node),
                        "line": node.location.start_line,
                    }
                    for node in function_nodes
                ],
            },
        )

        entry = FlowchartNode(
            node_id="node-0",
            kind=FlowchartNodeKind.START,
            label="START",
            source_text="start",
            source_file=result.file_path,
        )
        graph.nodes.append(entry)
        node_by_id = {entry.node_id: entry}
        terminal_nodes: list[str] = []

        def make_node(
            ast_node: ASTNode | None,
            kind: FlowchartNodeKind,
            label: str,
        ) -> FlowchartNode:
            node_id = f"node-{len(graph.nodes)}"
            item = FlowchartNode(
                node_id=node_id,
                kind=kind,
                label=label,
                source_text=exact_source(ast_node) if ast_node else "",
                source_file=result.file_path,
                line=ast_node.location.start_line if ast_node else None,
                column=ast_node.location.start_column if ast_node else None,
                metadata={"ast_type": ast_node.node_type} if ast_node else {},
            )
            graph.nodes.append(item)
            node_by_id[node_id] = item
            return item

        def connect(
            source_id: str,
            target_id: str,
            *,
            branch_label: str | None = None,
            edge_type: str = "normal",
        ) -> None:
            edge_id = f"edge-{len(graph.edges)}"
            graph.edges.append(
                FlowchartEdge(
                    edge_id=edge_id,
                    source_id=source_id,
                    target_id=target_id,
                    edge_type=edge_type,
                    branch_label=branch_label,
                    source_file=result.file_path,
                )
            )
            node_by_id[source_id].outgoing.append(edge_id)
            node_by_id[target_id].incoming.append(edge_id)

        def connect_incoming(
            incoming: list[tuple[str, str | None, str]], target_id: str
        ) -> None:
            for source_id, branch_label, edge_type in incoming:
                connect(
                    source_id,
                    target_id,
                    branch_label=branch_label,
                    edge_type=edge_type,
                )

        def branch_nodes(node: ASTNode) -> list[ASTNode]:
            if node.node_type == "else_clause":
                return node.children
            if node.node_type in self._BLOCK_TYPES:
                return node.children
            return [node]

        def sequence(
            statements: list[ASTNode],
            incoming: list[tuple[str, str | None, str]],
            loop_stack: list[dict[str, list[str]]],
        ) -> list[str]:
            pending = incoming
            for statement in statements:
                if not pending:
                    break
                exits = build_statement(statement, pending, loop_stack)
                pending = [(node_id, None, "normal") for node_id in exits]
            return [node_id for node_id, _label, _kind in pending]

        def build_if(
            ast_node: ASTNode,
            incoming: list[tuple[str, str | None, str]],
            loop_stack: list[dict[str, list[str]]],
        ) -> list[str]:
            alternatives = [
                child for child in ast_node.children
                if child.node_type in self._ELSE_TYPES
            ]
            condition = next(
                (
                    child for child in ast_node.children
                    if child not in alternatives
                    and child.node_type not in self._BLOCK_TYPES
                ),
                None,
            )
            then_nodes = [
                child for child in ast_node.children
                if child is not condition and child not in alternatives
            ]
            condition_text = exact_source(condition) if condition else exact_source(ast_node)
            decision = make_node(
                ast_node, FlowchartNodeKind.DECISION, f"IF {condition_text}"
            )
            connect_incoming(incoming, decision.node_id)

            then_statements = [
                nested for branch in then_nodes for nested in branch_nodes(branch)
            ]
            then_exits = (
                sequence(
                    then_statements,
                    [(decision.node_id, "yes", "decision")],
                    loop_stack,
                )
                if then_statements
                else []
            )
            else_exits: list[str] = []
            else_statements: list[ASTNode] = []
            if alternatives:
                else_statements = branch_nodes(alternatives[0])
                if else_statements:
                    else_exits = sequence(
                        else_statements,
                        [(decision.node_id, "no", "decision")],
                        loop_stack,
                    )

            needs_join = not alternatives or then_exits or else_exits
            if not needs_join:
                return []
            merge = make_node(ast_node, FlowchartNodeKind.MERGE, "MERGE")
            for exit_id in then_exits + else_exits:
                connect(exit_id, merge.node_id)
            if not then_statements:
                connect(
                    decision.node_id, merge.node_id,
                    branch_label="yes", edge_type="decision",
                )
            if not alternatives or not else_statements:
                connect(
                    decision.node_id, merge.node_id,
                    branch_label="no", edge_type="decision",
                )
            return [merge.node_id]

        def build_loop(
            ast_node: ASTNode,
            incoming: list[tuple[str, str | None, str]],
            loop_stack: list[dict[str, list[str]]],
        ) -> list[str]:
            body = next(
                (
                    child for child in reversed(ast_node.children)
                    if child.node_type in self._BLOCK_TYPES
                ),
                ast_node.children[-1] if ast_node.children else None,
            )
            label = exact_source(ast_node)
            if body is not None and source_bytes is not None:
                label = source_bytes[
                    ast_node.location.start_byte : body.location.start_byte
                ].decode("utf-8", errors="replace").strip().rstrip("{: ")
            loop = make_node(ast_node, FlowchartNodeKind.LOOP, label or "LOOP")
            connect_incoming(incoming, loop.node_id)
            loop_context = {"breaks": [], "continues": []}
            body_statements = branch_nodes(body) if body is not None else []
            body_exits = sequence(
                body_statements,
                [(loop.node_id, "yes", "loop")],
                loop_stack + [loop_context],
            )
            merge = make_node(ast_node, FlowchartNodeKind.MERGE, "LOOP EXIT")
            connect(
                loop.node_id, merge.node_id,
                branch_label="no", edge_type="loop-exit",
            )
            for exit_id in body_exits + loop_context["continues"]:
                connect(exit_id, loop.node_id, edge_type="loop-back")
            for break_id in loop_context["breaks"]:
                connect(
                    break_id, merge.node_id,
                    branch_label="break", edge_type="break",
                )
            if not body_statements:
                connect(loop.node_id, loop.node_id, branch_label="yes", edge_type="loop-back")
            return [merge.node_id]

        def build_statement(
            ast_node: ASTNode,
            incoming: list[tuple[str, str | None, str]],
            loop_stack: list[dict[str, list[str]]],
        ) -> list[str]:
            node_type = ast_node.node_type
            if node_type in self._BLOCK_TYPES:
                return sequence(ast_node.children, incoming, loop_stack)
            if node_type in self._IF_TYPES or node_type in {"elif_clause", "else_if_clause"}:
                return build_if(ast_node, incoming, loop_stack)
            if node_type == "else_clause":
                return sequence(ast_node.children, incoming, loop_stack)
            if node_type in self._LOOP_TYPES:
                return build_loop(ast_node, incoming, loop_stack)

            if node_type in self._RETURN_TYPES:
                item = make_node(
                    ast_node,
                    FlowchartNodeKind.RETURN,
                    f"RETURN: {exact_source(ast_node)}",
                )
                connect_incoming(incoming, item.node_id)
                terminal_nodes.append(item.node_id)
                return []
            if node_type in self._THROW_TYPES:
                item = make_node(
                    ast_node,
                    FlowchartNodeKind.EXCEPTION,
                    exact_source(ast_node) or "THROW",
                )
                connect_incoming(incoming, item.node_id)
                terminal_nodes.append(item.node_id)
                return []
            if node_type in self._BREAK_TYPES | self._CONTINUE_TYPES:
                in_loop = bool(loop_stack)
                kind = (
                    FlowchartNodeKind.BREAK
                    if node_type in self._BREAK_TYPES
                    else FlowchartNodeKind.CONTINUE
                )
                item = make_node(ast_node, kind, exact_source(ast_node).upper())
                if not in_loop:
                    item.metadata["unsupported"] = "loop control outside a loop"
                    item.label = f"UNSUPPORTED: {item.label}"
                connect_incoming(incoming, item.node_id)
                if in_loop:
                    target_key = "breaks" if kind == FlowchartNodeKind.BREAK else "continues"
                    loop_stack[-1][target_key].append(item.node_id)
                    return []
                return [item.node_id]

            if node_type in self._FUNCTION_TYPES:
                label = f"FUNCTION: {self._function_name(ast_node)}"
                item = make_node(ast_node, FlowchartNodeKind.FUNCTION, label)
                connect_incoming(incoming, item.node_id)
                return [item.node_id]

            if node_type in {"comment", "line_comment", "block_comment"}:
                return [source_id for source_id, _label, _kind in incoming]

            kind = FlowchartNodeKind.PROCESS
            label = exact_source(ast_node) or ast_node.display_name
            if node_type in self._CALL_TYPES or any(
                child.node_type in self._CALL_TYPES for child in ast_node.walk()
            ):
                call = next(
                    child for child in ast_node.walk()
                    if child.node_type in self._CALL_TYPES
                )
                callee = exact_source(call.children[0]).split("(", 1)[0].strip() if call.children else ""
                short_name = callee.rsplit(".", 1)[-1].lower()
                if short_name in self._OUTPUT_CALLS:
                    kind = FlowchartNodeKind.OUTPUT
                    label = f"OUTPUT: {exact_source(ast_node)}"
                elif short_name in self._INPUT_CALLS:
                    kind = FlowchartNodeKind.INPUT
                    label = f"INPUT: {exact_source(ast_node)}"
                else:
                    kind = FlowchartNodeKind.FUNCTION
                    label = f"CALL: {exact_source(ast_node)}"

            item = make_node(ast_node, kind, label)
            if node_type not in self._ATOMIC_TYPES:
                item.metadata["unsupported"] = node_type
                item.label = f"UNSUPPORTED {node_type}: {label}"
            connect_incoming(incoming, item.node_id)
            return [item.node_id]

        scope_statements = self._function_body(function) if function else result.root.children
        exits = sequence(scope_statements, [(entry.node_id, None, "normal")], [])
        end = make_node(None, FlowchartNodeKind.END, "END")
        for exit_id in exits + terminal_nodes:
            connect(exit_id, end.node_id)
        if not exits and not terminal_nodes:
            connect(entry.node_id, end.node_id)
        graph.entry = entry.node_id
        graph.exit_nodes = [end.node_id]
        graph.metadata["node_count"] = len(graph.nodes)
        return graph


__all__ = ["FlowchartBuilder"]
