from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..model import ASTNode, ASTResult


@dataclass(frozen=True, slots=True)
class VariableDefinition:
    variable_id: str
    name: str
    scope: str
    kind: str
    source_file: Path | None
    source_node: ASTNode | None
    line: int | None = None
    column: int | None = None
    expression: str = ""


@dataclass(frozen=True, slots=True)
class VariableUse:
    variable_id: str
    name: str
    scope: str
    source_file: Path | None
    source_node: ASTNode | None
    line: int | None = None
    column: int | None = None
    kind: str = "read"


@dataclass(frozen=True, slots=True)
class VariableFlowFact:
    variable_id: str
    name: str
    scope: str
    kind: str
    source_file: Path | None
    declaration: VariableDefinition | None = None
    definitions: tuple[VariableDefinition, ...] = ()
    uses: tuple[VariableUse, ...] = ()


@dataclass(slots=True)
class VariableFlowAnalysis:
    source_file: Path | None
    language: str
    facts: list[VariableFlowFact] = field(default_factory=list)

    @staticmethod
    def _scope_name(node: ASTNode, nodes_by_id: dict[str, ASTNode]) -> str:
        current: ASTNode | None = node
        while current is not None:
            parent = nodes_by_id.get(current.parent_id) if current.parent_id is not None else None
            if parent is not None and parent.node_type in {"function_definition", "method_definition"}:
                for child in parent.children:
                    if child.node_type in {"identifier", "name"}:
                        return child.source_text.strip() or "function"
                return "function"
            current = parent
        return "module"

    @staticmethod
    def _assignment_target(node: ASTNode) -> str | None:
        if node.node_type in {"assignment", "assignment_expression", "augmented_assignment"}:
            for child in node.children:
                if child.node_type in {"identifier", "name"}:
                    return child.source_text.strip()
        if node.node_type in {"declaration", "variable_declaration", "init_declarator"}:
            for child in node.children:
                if child.node_type in {"identifier", "name"}:
                    return child.source_text.strip()
        if node.node_type == "parameter":
            return node.source_text.strip()
        return None

    @staticmethod
    def _is_function_call_name(node: ASTNode, nodes_by_id: dict[str, ASTNode]) -> bool:
        parent = nodes_by_id.get(node.parent_id) if node.parent_id is not None else None
        if parent is None:
            return False
        if parent.node_type == "call" and parent.children and parent.children[0].node_id == node.node_id:
            return True
        return False

    @staticmethod
    def _is_definition_usage(node: ASTNode, nodes_by_id: dict[str, ASTNode]) -> bool:
        parent = nodes_by_id.get(node.parent_id) if node.parent_id is not None else None
        if parent is None:
            return False
        if parent.node_type in {"assignment", "assignment_expression", "augmented_assignment"}:
            return any(child.node_id == node.node_id for child in parent.children[1:])
        if parent.node_type in {"binary_operator", "comparison_operator", "unary_expression"}:
            return True
        return True

    def analyze(self, result: ASTResult) -> "VariableFlowAnalysis":
        variables: dict[tuple[str, str], VariableFlowFact] = {}
        nodes_by_id = {node.node_id: node for node in result.root.walk()}

        def ensure_fact(name: str, scope: str, source_node: ASTNode | None, kind: str) -> VariableFlowFact:
            key = (scope, name)
            fact = variables.get(key)
            if fact is not None:
                return fact
            fact = VariableFlowFact(
                variable_id=f"{result.file_path or 'unknown'}:{scope}:{name}",
                name=name,
                scope=scope,
                kind=kind,
                source_file=result.file_path,
                declaration=None,
                definitions=(),
                uses=(),
            )
            variables[key] = fact
            return fact

        for node in result.root.walk():
            if node.node_type in {"assignment", "assignment_expression", "augmented_assignment", "declaration", "variable_declaration", "init_declarator", "parameter"}:
                name = self._assignment_target(node)
                if not name:
                    continue
                scope = self._scope_name(node, nodes_by_id)
                fact = ensure_fact(name, scope, node, "local")
                if node.node_type == "parameter":
                    fact_kind = "parameter"
                elif node.node_type in {"declaration", "variable_declaration", "init_declarator"}:
                    fact_kind = "local"
                else:
                    fact_kind = "local"
                def_entry = VariableDefinition(
                    variable_id=fact.variable_id,
                    name=name,
                    scope=scope,
                    kind=fact_kind,
                    source_file=result.file_path,
                    source_node=node,
                    line=node.location.start_line,
                    column=node.location.start_column,
                    expression=node.source_text.strip(),
                )
                declarations = list(fact.definitions)
                declarations.append(def_entry)
                object.__setattr__(fact, "definitions", tuple(declarations))
                if fact.declaration is None:
                    object.__setattr__(fact, "declaration", def_entry)
                if fact.kind == "local" and fact_kind != "local":
                    object.__setattr__(fact, "kind", fact_kind)

            if node.node_type in {"identifier", "name"}:
                name = node.source_text.strip()
                if not name or name in {"if", "return", "print", "def", "class"}:
                    continue
                parent = nodes_by_id.get(node.parent_id) if node.parent_id is not None else None
                if parent is not None and parent.node_type in {"function_definition", "function_declarator", "parameter", "parameter_list", "declaration", "variable_declaration", "init_declarator"}:
                    continue
                if self._is_function_call_name(node, nodes_by_id):
                    continue
                scope = self._scope_name(node, nodes_by_id)
                if parent is not None and parent.node_type in {"assignment", "assignment_expression", "augmented_assignment"}:
                    target_name = self._assignment_target(parent)
                    if target_name == name and any(child.node_id == node.node_id for child in parent.children):
                        continue
                fact = ensure_fact(name, scope, node, "local")
                uses = list(fact.uses)
                uses.append(
                    VariableUse(
                        variable_id=fact.variable_id,
                        name=name,
                        scope=scope,
                        source_file=result.file_path,
                        source_node=node,
                        line=node.location.start_line,
                        column=node.location.start_column,
                        kind="read",
                    )
                )
                object.__setattr__(fact, "uses", tuple(uses))

        self.facts = sorted(variables.values(), key=lambda fact: (fact.scope, fact.name))
        return self


__all__ = [
    "VariableDefinition",
    "VariableFlowAnalysis",
    "VariableFlowFact",
    "VariableUse",
]
