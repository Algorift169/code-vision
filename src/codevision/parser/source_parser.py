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
        if not language_info.supports_parsing:
            target = language_info.display_name or language or str(path or "")
            raise ValueError(f"AST analysis does not support: {target or 'unknown source'}")
        source_bytes = source.encode("utf-8") if isinstance(source, str) else source
        if not isinstance(source_bytes, bytes):
            raise TypeError("Source must be str or bytes")

        if language_info.language_id == "asm":
            return self._parse_assembly_fallback(source_bytes, path, language_info.language_id)

        parsed = self._native_parser.parse(source_bytes, language_info.language_id)
        root_native = parsed.tree.root_node
        next_id = 0
        syntax_error_count = 0

        def make_node(native_node: object, parent_id: str | None) -> ASTNode:
            nonlocal next_id, syntax_error_count
            node_id = str(next_id)
            next_id += 1
            start_byte = native_node.start_byte
            end_byte = native_node.end_byte
            start_prefix = source_bytes[:start_byte]
            end_prefix = source_bytes[:end_byte]
            start_line = start_prefix.count(b"\n") + 1
            end_line = end_prefix.count(b"\n") + 1
            start_column = len(start_prefix.rsplit(b"\n", 1)[-1]) + 1
            end_column = len(end_prefix.rsplit(b"\n", 1)[-1]) + 1
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
                    start_line=start_line,
                    start_column=start_column,
                    end_line=end_line,
                    end_column=end_column,
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
    def _parse_assembly_fallback(
        source_bytes: bytes,
        file_path: Path | None,
        language_id: str,
    ) -> ASTResult:
        source_text = source_bytes.decode("utf-8", errors="replace")
        lines = source_text.splitlines() or [""]

        def location_for(line_number: int, text: str, start_offset: int) -> SourceLocation:
            line_start = sum(len(line) + 1 for line in lines[: line_number - 1])
            start_column = len(lines[line_number - 1][: start_offset]) + 1
            end_column = start_column + len(text)
            return SourceLocation(
                start_line=line_number,
                start_column=start_column,
                end_line=line_number,
                end_column=end_column,
                start_byte=line_start + start_offset,
                end_byte=line_start + start_offset + len(text),
            )

        root = ASTNode(
            node_id="0",
            node_type="translation_unit",
            display_name="Translation Unit",
            source_text=source_text[:180],
            location=SourceLocation(
                start_line=1,
                start_column=1,
                end_line=max(1, len(lines)),
                end_column=max(1, len(lines[-1]) + 1),
                start_byte=0,
                end_byte=len(source_text.encode("utf-8")),
            ),
            parent_id=None,
        )
        next_id = 1
        current_label: ASTNode | None = None

        for line_number, raw_line in enumerate(lines, 1):
            text = raw_line.rstrip("\r\n")
            if not text.strip():
                continue
            if text.lstrip().startswith("."):
                current_label = None
                node_type = "directive"
                name = "Directive"
                directive_text = text.strip()
                node = ASTNode(
                    node_id=str(next_id),
                    node_type=node_type,
                    display_name=f"{name}: {directive_text}",
                    source_text=directive_text,
                    location=location_for(
                        line_number, directive_text, raw_line.find(directive_text)
                    ),
                    parent_id=root.node_id,
                )
                next_id += 1
                root.children.append(node)
                continue

            label_name = None
            instruction_text = text
            if ":" in text:
                label_text, _, remainder = text.partition(":")
                label_name = label_text.strip()
                if label_name:
                    current_label = ASTNode(
                        node_id=str(next_id),
                        node_type="label_definition",
                        display_name=f"Label: {label_name}",
                        source_text=label_name,
                        location=location_for(
                            line_number,
                            label_name,
                            raw_line.find(label_name),
                        ),
                        parent_id=root.node_id,
                    )
                    next_id += 1
                    root.children.append(current_label)
                    instruction_text = remainder.strip()
                    if instruction_text:
                        instruction_node = ASTNode(
                            node_id=str(next_id),
                            node_type="instruction",
                            display_name=f"Instruction: {instruction_text}",
                            source_text=instruction_text,
                            location=location_for(
                                line_number,
                                instruction_text,
                                raw_line.find(instruction_text),
                            ),
                            parent_id=current_label.node_id,
                        )
                        next_id += 1
                        current_label.children.append(instruction_node)
                    continue

            if current_label is not None:
                instruction_node = ASTNode(
                    node_id=str(next_id),
                    node_type="instruction",
                    display_name=f"Instruction: {instruction_text}",
                    source_text=instruction_text,
                    location=location_for(
                        line_number,
                        instruction_text,
                        raw_line.find(instruction_text),
                    ),
                    parent_id=current_label.node_id,
                )
                next_id += 1
                current_label.children.append(instruction_node)
                continue

            instruction_node = ASTNode(
                node_id=str(next_id),
                node_type="instruction",
                display_name=f"Instruction: {instruction_text}",
                source_text=instruction_text,
                location=location_for(
                    line_number,
                    instruction_text,
                    raw_line.find(instruction_text),
                ),
                parent_id=root.node_id,
            )
            next_id += 1
            root.children.append(instruction_node)

        nodes = tuple(root.walk())
        max_depth = 0
        depth_by_id: dict[str, int] = {root.node_id: 1}
        for node in nodes:
            depth = depth_by_id.get(node.parent_id, 1) + 1 if node.parent_id is not None else 1
            depth_by_id[node.node_id] = depth
            max_depth = max(max_depth, depth)
        return ASTResult(
            root=root,
            language=language_id,
            file_path=file_path,
            node_count=len(nodes),
            max_depth=max_depth,
            parse_duration_ms=0.0,
            syntax_error_count=0,
            errors=(),
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
