from __future__ import annotations

from ..model import ASTNode, ASTResult
from .flowchart_ir import FlowchartEdge, FlowchartGraph, FlowchartNode, FlowchartNodeKind


class FlowchartBuilder:
    """Translate AST nodes into a deterministic flowchart graph."""

    def build(
        self,
        result: ASTResult,
        source: str | bytes | None = None,
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

        def control_header(node: ASTNode) -> str:
            body = next(
                (
                    child
                    for child in node.children
                    if child.node_type in {"compound_statement", "block"}
                ),
                None,
            )
            if source_bytes is not None and body is not None:
                header = source_bytes[
                    node.location.start_byte : body.location.start_byte
                ].decode("utf-8", errors="replace")
                return " ".join(header.split()).rstrip("{: ")
            if node.node_type == "if_statement":
                condition = next(
                    (
                        child
                        for child in node.children
                        if child.node_type not in {"else_clause", "compound_statement", "block"}
                    ),
                    None,
                )
                if condition is not None:
                    return f"IF {exact_source(condition)}"
            return exact_source(node)

        graph = FlowchartGraph(
            graph_id=f"flowchart-{result.file_path.name if result.file_path else 'source'}",
            source_file=result.file_path,
            language=result.language,
            nodes=[],
            edges=[],
            entry=None,
            exit_nodes=[],
            metadata={"node_count": 0},
        )

        entry = FlowchartNode(
            node_id="node-0",
            kind=FlowchartNodeKind.START,
            label="START",
            source_text="start",
            source_file=result.file_path,
        )
        graph.nodes.append(entry)
        graph.entry = entry.node_id

        def label_for(node: ASTNode, kind: FlowchartNodeKind) -> str:
            if kind == FlowchartNodeKind.DECISION:
                condition = next(
                    (
                        child
                        for child in node.children
                        if child.node_type not in {"else_clause", "compound_statement", "block"}
                    ),
                    None,
                )
                text = f"IF {exact_source(condition)}" if condition else control_header(node)
            elif kind in {FlowchartNodeKind.LOOP, FlowchartNodeKind.FUNCTION}:
                text = control_header(node)
            else:
                text = exact_source(node) or node.display_name
            if kind == FlowchartNodeKind.RETURN:
                return f"RETURN: {text}"
            if kind == FlowchartNodeKind.LOOP:
                return text
            return text or kind.value.upper()

        def make_node(ast_node: ASTNode, kind: FlowchartNodeKind) -> FlowchartNode:
            item = FlowchartNode(
                node_id=f"node-{len(graph.nodes)}",
                kind=kind,
                label=label_for(ast_node, kind),
                source_text=exact_source(ast_node),
                source_file=result.file_path,
                line=ast_node.location.start_line,
                column=ast_node.location.start_column,
            )
            graph.nodes.append(item)
            return item

        def connect(source_id: str, target_id: str, *, branch_label: str | None = None, edge_type: str = "normal") -> None:
            graph.edges.append(
                FlowchartEdge(
                    edge_id=f"edge-{len(graph.edges)}",
                    source_id=source_id,
                    target_id=target_id,
                    edge_type=edge_type,
                    branch_label=branch_label,
                    source_file=result.file_path,
                )
            )

        def walk(ast_node: ASTNode, parent_id: str | None = None) -> str | None:
            node_kind = FlowchartNodeKind.PROCESS
            if ast_node.node_type == "if_statement":
                node_kind = FlowchartNodeKind.DECISION
            elif ast_node.node_type == "return_statement":
                node_kind = FlowchartNodeKind.RETURN
            elif ast_node.node_type in {"for_statement", "while_statement"}:
                node_kind = FlowchartNodeKind.LOOP
            elif ast_node.node_type == "function_definition":
                node_kind = FlowchartNodeKind.FUNCTION
            elif ast_node.node_type in {"break_statement"}:
                node_kind = FlowchartNodeKind.BREAK
            elif ast_node.node_type in {"continue_statement"}:
                node_kind = FlowchartNodeKind.CONTINUE
            elif ast_node.node_type in {"call_expression"}:
                node_kind = FlowchartNodeKind.FUNCTION

            if ast_node.node_type in {"translation_unit", "compound_statement"}:
                current_parent = parent_id
                for child in ast_node.children:
                    current_parent = walk(child, current_parent)
                return current_parent

            if ast_node.node_type == "if_statement":
                decision = make_node(ast_node, FlowchartNodeKind.DECISION)
                if parent_id is not None:
                    connect(parent_id, decision.node_id)
                else:
                    connect(entry.node_id, decision.node_id)
                yes_target = None
                no_target = None
                for child in ast_node.children:
                    if child.node_type in {"compound_statement", "if_statement", "return_statement", "for_statement", "while_statement"}:
                        branch_node = walk(child, decision.node_id)
                        if yes_target is None:
                            yes_target = branch_node
                    elif child.node_type == "else_clause":
                        if child.children:
                            no_target = walk(child.children[0], decision.node_id)
                if yes_target is not None:
                    connect(decision.node_id, yes_target, branch_label="yes", edge_type="decision")
                if no_target is not None:
                    connect(decision.node_id, no_target, branch_label="no", edge_type="decision")
                return decision.node_id

            if ast_node.node_type == "return_statement":
                current = make_node(ast_node, FlowchartNodeKind.RETURN)
                if parent_id is not None:
                    connect(parent_id, current.node_id)
                else:
                    connect(entry.node_id, current.node_id)
                return current.node_id

            if ast_node.node_type in {"for_statement", "while_statement"}:
                current = make_node(ast_node, FlowchartNodeKind.LOOP)
                if parent_id is not None:
                    connect(parent_id, current.node_id)
                else:
                    connect(entry.node_id, current.node_id)
                for child in ast_node.children:
                    if child.node_type not in {"compound_statement", "declaration"}:
                        walk(child, current.node_id)
                return current.node_id

            if ast_node.node_type == "function_definition":
                current = make_node(ast_node, FlowchartNodeKind.FUNCTION)
                if parent_id is not None:
                    connect(parent_id, current.node_id)
                else:
                    connect(entry.node_id, current.node_id)
                for child in ast_node.children:
                    walk(child, current.node_id)
                return current.node_id

            if ast_node.node_type in {"break_statement", "continue_statement"}:
                current = make_node(ast_node, FlowchartNodeKind.BREAK if ast_node.node_type == "break_statement" else FlowchartNodeKind.CONTINUE)
                if parent_id is not None:
                    connect(parent_id, current.node_id)
                return current.node_id

            if ast_node.node_type not in {"identifier", "parameter_list", "declaration", "type"}:
                current = make_node(ast_node, FlowchartNodeKind.PROCESS)
                if parent_id is not None:
                    connect(parent_id, current.node_id)
                else:
                    connect(entry.node_id, current.node_id)
                for child in ast_node.children:
                    walk(child, current.node_id)
                return current.node_id

            for child in ast_node.children:
                walk(child, parent_id)
            return parent_id

        for child in result.root.children:
            walk(child, entry.node_id)

        end = FlowchartNode(
            node_id=f"node-{len(graph.nodes)}",
            kind=FlowchartNodeKind.END,
            label="END",
            source_text="end",
            source_file=result.file_path,
        )
        graph.nodes.append(end)
        graph.entry = entry.node_id
        graph.exit_nodes = [end.node_id]

        last_node = graph.nodes[-2] if len(graph.nodes) >= 2 else entry
        connect(last_node.node_id, end.node_id)
        graph.metadata["node_count"] = len(graph.nodes)
        return graph


__all__ = ["FlowchartBuilder"]
