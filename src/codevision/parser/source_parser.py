from __future__ import annotations

from pathlib import Path

from ..model import ASTNode, ASTResult, SourceLocation
from .language_registry import LanguageRegistry
from .tree_sitter_parser import TreeSitterParser


_DISPLAY_NAMES = {
    "translation_unit": "Translation Unit",
    "preproc_include": "Preprocessor Include",
    "preproc_def": "Macro Definition",
    "function_definition": "Function Definition",
    "function_declarator": "Function Declarator",
    "parameter_list": "Parameters",
    "declaration": "Declaration",
    "type_definition": "Typedef Declaration",
    "struct_specifier": "Struct Declaration",
    "union_specifier": "Union Declaration",
    "enum_specifier": "Enum Declaration",
    "class_specifier": "Class Declaration",
    "namespace_definition": "Namespace",
    "compound_statement": "Compound Statement",
    "call_expression": "Function Call",
    "if_statement": "If Statement",
    "else_clause": "Else Clause",
    "for_statement": "For Loop",
    "while_statement": "While Loop",
    "do_statement": "Do-While Loop",
    "switch_statement": "Switch Statement",
    "case_statement": "Case Statement",
    "return_statement": "Return Statement",
    "break_statement": "Break Statement",
    "continue_statement": "Continue Statement",
    "assignment_expression": "Assignment",
    "binary_expression": "Binary Expression",
    "unary_expression": "Unary Expression",
    "pointer_declarator": "Pointer Declaration",
    "array_declarator": "Array Declaration",
    "subscript_expression": "Array Access",
    "field_expression": "Member Access",
    "template_declaration": "Template Declaration",
    "constructor_or_destructor_definition": "Constructor / Destructor",
    "ERROR": "Syntax Error",
}


class SourceParser:
    """Parse C/C++ source and normalize its named syntax tree."""

    def __init__(self) -> None:
        self._native_parser = TreeSitterParser()

    def parse(
        self,
        source: str | bytes,
        language: str | None = None,
        file_path: str | Path | None = None,
    ) -> ASTResult:
        path = Path(file_path).expanduser().resolve() if file_path is not None else None
        language_info = LanguageRegistry.resolve(language, path)
        if language_info is None:
            target = language if language is not None else str(path or "")
            raise ValueError(f"AST analysis does not support: {target or 'unknown source'}")
        source_bytes = source.encode("utf-8") if isinstance(source, str) else source
        if not isinstance(source_bytes, bytes):
            raise TypeError("Source must be str or bytes")

        parsed = self._native_parser.parse(source_bytes, language_info.language_id)
        root_native = parsed.tree.root_node
        next_id = 0
        syntax_error_count = 0

        def make_node(native_node: object, parent_id: str | None) -> ASTNode:
            nonlocal next_id, syntax_error_count
            node_id = str(next_id)
            next_id += 1
            start_point = native_node.start_point
            end_point = native_node.end_point
            start_byte = native_node.start_byte
            end_byte = native_node.end_byte
            node_type = str(native_node.type)
            has_error = bool(native_node.is_error)
            is_missing = bool(native_node.is_missing)
            if native_node.is_error or is_missing:
                syntax_error_count += 1
            raw = source_bytes[start_byte : min(end_byte, start_byte + 512)].decode(
                "utf-8", errors="replace"
            )
            source_text = " ".join(raw.split())[:180]
            name = self._display_name(node_type, source_text)
            node = ASTNode(
                node_id=node_id,
                node_type=node_type,
                display_name=name,
                source_text=source_text,
                location=SourceLocation(
                    start_line=start_point.row + 1,
                    start_column=start_point.column + 1,
                    end_line=end_point.row + 1,
                    end_column=end_point.column + 1,
                    start_byte=start_byte,
                    end_byte=end_byte,
                ),
                parent_id=parent_id,
                has_error=has_error,
                is_missing=is_missing,
            )
            return node

        root = make_node(root_native, None)
        stack: list[tuple[object, ASTNode]] = [(root_native, root)]
        while stack:
            native_parent, parent = stack.pop()
            pending: list[tuple[object, ASTNode]] = []
            for native_child in native_parent.children:
                if not (
                    native_child.is_named
                    or native_child.is_error
                    or native_child.is_missing
                ):
                    continue
                child = make_node(native_child, parent.node_id)
                parent.children.append(child)
                pending.append((native_child, child))
            stack.extend(reversed(pending))
        nodes = tuple(root.walk())
        depth_by_id: dict[str, int] = {}
        max_depth = 0
        for node in nodes:
            depth = 1 if node.parent_id is None else depth_by_id[node.parent_id] + 1
            depth_by_id[node.node_id] = depth
            max_depth = max(max_depth, depth)
        if bool(root_native.has_error) and syntax_error_count == 0:
            syntax_error_count = 1
        errors = (
            (f"Tree-sitter found {syntax_error_count} syntax error or missing node.",)
            if syntax_error_count
            else ()
        )
        return ASTResult(
            root=root,
            language=language_info.language_id,
            file_path=path,
            node_count=len(nodes),
            max_depth=max_depth,
            parse_duration_ms=parsed.duration_ms,
            syntax_error_count=syntax_error_count,
            errors=errors,
        )

    @staticmethod
    def _display_name(node_type: str, source_text: str) -> str:
        base = _DISPLAY_NAMES.get(
            node_type,
            " ".join(part.capitalize() for part in node_type.split("_")),
        )
        if node_type in {
            "function_definition",
            "function_declarator",
            "struct_specifier",
            "union_specifier",
            "enum_specifier",
            "class_specifier",
            "namespace_definition",
            "call_expression",
            "declaration",
        } and source_text:
            summary = source_text.split("{", 1)[0].strip()
            if len(summary) > 48:
                summary = f"{summary[:45]}..."
            return f"{base}: {summary}"
        if node_type == "identifier" and source_text:
            return f"Identifier: {source_text}"
        return base
