from __future__ import annotations

from dataclasses import dataclass

from ..model import ASTNode, ASTResult


@dataclass(frozen=True, slots=True)
class ASTFacts:
    preprocessor: tuple[ASTNode, ...]
    globals: tuple[ASTNode, ...]
    constants: tuple[ASTNode, ...]
    structs: tuple[ASTNode, ...]
    unions: tuple[ASTNode, ...]
    enums: tuple[ASTNode, ...]
    typedefs: tuple[ASTNode, ...]
    classes: tuple[ASTNode, ...]
    namespaces: tuple[ASTNode, ...]
    functions: tuple[ASTNode, ...]
    parameters: tuple[ASTNode, ...]
    locals: tuple[ASTNode, ...]
    calls: tuple[ASTNode, ...]
    returns: tuple[ASTNode, ...]
    conditionals: tuple[ASTNode, ...]
    loops: tuple[ASTNode, ...]
    switches: tuple[ASTNode, ...]
    loop_control: tuple[ASTNode, ...]
    assignments: tuple[ASTNode, ...]
    operators: tuple[ASTNode, ...]
    pointers: tuple[ASTNode, ...]
    arrays: tuple[ASTNode, ...]
    member_accesses: tuple[ASTNode, ...]
    templates: tuple[ASTNode, ...]


class ASTExtractor:
    """Group normalized nodes by their C/C++ structural role."""

    def extract(self, result: ASTResult) -> ASTFacts:
        nodes = tuple(result.root.walk())
        types = {
            "preprocessor": {"preproc_include", "preproc_def", "preproc_function_def"},
            "constants": {"const_declaration"},
            "structs": {"struct_specifier"},
            "unions": {"union_specifier"},
            "enums": {"enum_specifier"},
            "typedefs": {"type_definition"},
            "classes": {"class_specifier"},
            "namespaces": {"namespace_definition"},
            "functions": {"function_definition", "function_declaration"},
            "parameters": {"parameter_declaration"},
            "calls": {"call_expression"},
            "returns": {"return_statement", "co_return_statement"},
            "conditionals": {"if_statement", "conditional_expression"},
            "loops": {
                "for_statement",
                "for_range_loop",
                "while_statement",
                "do_statement",
            },
            "switches": {"switch_statement", "case_statement"},
            "loop_control": {"break_statement", "continue_statement"},
            "assignments": {"assignment_expression", "init_declarator"},
            "operators": {"binary_expression", "unary_expression"},
            "pointers": {"pointer_declarator", "pointer_expression"},
            "arrays": {"array_declarator", "subscript_expression"},
            "member_accesses": {"field_expression", "qualified_identifier"},
            "templates": {"template_declaration", "template_instantiation"},
        }
        grouped = {
            category: tuple(node for node in nodes if node.node_type in node_types)
            for category, node_types in types.items()
        }
        function_declaration_ids = self._function_declaration_ids(nodes)
        function_declarations = tuple(
            node for node in nodes if node.node_id in function_declaration_ids
        )
        grouped["functions"] += function_declarations
        function_ids = {node.node_id for node in grouped["functions"]}
        nodes_by_id = {node.node_id: node for node in nodes}
        variables = tuple(
            node
            for node in nodes
            if node.node_type == "declaration"
            and node.node_id not in function_ids
        )
        global_nodes: list[ASTNode] = []
        local_nodes: list[ASTNode] = []
        for node in variables:
            parent_id = node.parent_id
            inside_function = False
            while parent_id is not None:
                if parent_id in function_ids:
                    inside_function = True
                    break
                parent = nodes_by_id.get(parent_id)
                parent_id = parent.parent_id if parent is not None else None
            (local_nodes if inside_function else global_nodes).append(node)
        constants = tuple(
            node
            for node in nodes
            if node.node_type == "declaration"
            and "const" in node.source_text.split()
            and node.node_id not in function_ids
        )
        return ASTFacts(
            preprocessor=grouped["preprocessor"],
            globals=tuple(global_nodes),
            constants=constants,
            structs=grouped["structs"],
            unions=grouped["unions"],
            enums=grouped["enums"],
            typedefs=grouped["typedefs"],
            classes=grouped["classes"],
            namespaces=grouped["namespaces"],
            functions=grouped["functions"],
            parameters=grouped["parameters"],
            locals=tuple(local_nodes),
            calls=grouped["calls"],
            returns=grouped["returns"],
            conditionals=grouped["conditionals"],
            loops=grouped["loops"],
            switches=grouped["switches"],
            loop_control=grouped["loop_control"],
            assignments=grouped["assignments"],
            operators=grouped["operators"],
            pointers=grouped["pointers"],
            arrays=grouped["arrays"],
            member_accesses=grouped["member_accesses"],
            templates=grouped["templates"],
        )

    @staticmethod
    def _function_declaration_ids(nodes: tuple[ASTNode, ...]) -> set[str]:
        nodes_by_id = {node.node_id: node for node in nodes}
        declaration_ids = {
            node.node_id for node in nodes if node.node_type == "declaration"
        }
        function_declaration_ids: set[str] = set()
        for node in nodes:
            if node.node_type != "function_declarator":
                continue
            parent_id = node.parent_id
            while parent_id is not None:
                if parent_id in declaration_ids:
                    function_declaration_ids.add(parent_id)
                    break
                parent = nodes_by_id.get(parent_id)
                parent_id = parent.parent_id if parent is not None else None
        return function_declaration_ids
