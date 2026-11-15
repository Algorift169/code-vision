from __future__ import annotations

import math
import re
from pathlib import Path

from ..model import ASTNode, ASTResult
from ..parser import SourceParser
from .complexity_result import ComplexityReport, FunctionComplexity


class ComplexityAnalyzer:
    """Calculate lightweight but real static complexity metrics from an AST."""

    _FUNCTION_TYPES = {
        "function_definition",
        "function_declaration",
        "method_definition",
        "method_declaration",
        "constructor_declaration",
        "label_definition",
        "lambda_expression",
    }
    _DECISION_TYPES = {
        "if_statement",
        "else_clause",
        "for_statement",
        "while_statement",
        "do_statement",
        "switch_statement",
        "case_statement",
        "conditional_expression",
        "match_statement",
        "for_in_statement",
        "enhanced_for_statement",
    }
    _LOOP_TYPES = {"for_statement", "while_statement", "do_statement", "for_in_statement", "enhanced_for_statement"}
    _SEQUENTIAL_EXTRACTOR = re.compile(r"\b(?:for|while|if|switch|try|catch|return|yield|continue|break|throw)\b", re.IGNORECASE)
    _HALSTEAD_OPERATORS = {
        "=", "+", "-", "*", "/", "%", "==", "!=", "<", ">", "<=", ">=", "&&", "||",
        "!", "&", "|", "^", "<<", ">>", ".", ",", "(", ")", "[", "]", "{", "}", ";",
        ":", "?", "->", "in", "is", "not", "and", "or",
    }

    def analyze(self, source: str | None, file_path: str | Path | None = None, language: str | None = None) -> ComplexityReport:
        if source is None or not source.strip():
            return ComplexityReport(file_path=Path(file_path).expanduser().resolve() if file_path else None, language=language or "unknown")

        parser = SourceParser()
        result = parser.parse(source, language=language, file_path=file_path)
        return self._from_result(result, source)

    def _from_result(self, result: ASTResult, source: str) -> ComplexityReport:
        functions: list[FunctionComplexity] = []
        warnings: list[str] = []

        for node in result.root.walk():
            if node.node_type not in self._FUNCTION_TYPES:
                continue
            functions.append(self._measure_function(node, result, source))

        if not functions:
            warnings.append("No function-like nodes were found; results are limited to the file-level summary.")

        total_cyclomatic = sum(item.cyclomatic for item in functions)
        average_cyclomatic = (total_cyclomatic / len(functions)) if functions else 0.0
        total_cognitive = sum(item.cognitive for item in functions)
        average_cognitive = (total_cognitive / len(functions)) if functions else 0.0
        hotspots = sorted(functions, key=lambda item: (item.cyclomatic, item.cognitive), reverse=True)[:5]
        return ComplexityReport(
            file_path=result.file_path,
            language=result.language,
            functions=functions,
            total_cyclomatic=total_cyclomatic,
            average_cyclomatic=average_cyclomatic,
            total_cognitive=total_cognitive,
            average_cognitive=average_cognitive,
            hotspots=hotspots,
            warnings=warnings,
        )

    def _measure_function(self, node: ASTNode, result: ASTResult, source: str) -> FunctionComplexity:
        snippet = self._source_slice(source, node)
        name = self._function_name(node)
        line = node.location.start_line if node.location else 1

        decision_count = self._decision_count(node)
        cyclomatic = max(1, 1 + decision_count)
        cognitive = self._cognitive_score(node, 0)
        time_complexity = self._estimate_time(snippet, node)
        space_complexity = self._estimate_space(snippet)
        maintainability = self._maintainability(snippet, cyclomatic, cognitive)
        halstead_volume = self._halstead_volume(snippet)
        risk = self._risk_for(cyclomatic, cognitive)
        evidence = self._evidence(snippet, cyclomatic, cognitive)

        return FunctionComplexity(
            name=name,
            file_path=result.file_path,
            language=result.language,
            line=line,
            cyclomatic=cyclomatic,
            cognitive=cognitive,
            time_complexity=time_complexity,
            space_complexity=space_complexity,
            maintainability=maintainability,
            halstead_volume=halstead_volume,
            risk=risk,
            explanation=f"Cyclomatic {cyclomatic}; cognitive {cognitive}; time {time_complexity}; space {space_complexity}.",
            evidence=evidence,
        )

    @staticmethod
    def _source_slice(source: str, node: ASTNode) -> str:
        try:
            encoded = source.encode("utf-8")
            start = node.location.start_byte
            end = node.location.end_byte
            if end <= start:
                return node.source_text
            return encoded[start:end].decode("utf-8", errors="replace")
        except Exception:
            return node.source_text

    @staticmethod
    def _function_name(node: ASTNode) -> str:
        if node.node_type == "label_definition":
            label = (node.source_text or node.display_name).strip()
            return label.split(":", 1)[0].strip() or "label"
        for child in node.walk():
            if child.node_type in {"identifier", "name", "field_identifier", "type_identifier"}:
                text = child.source_text.strip()
                if text:
                    return text
        return node.display_name or "anonymous_function"

    def _decision_count(self, node: ASTNode) -> int:
        count = 0
        for child in node.walk():
            if child.node_type in self._DECISION_TYPES:
                count += 1
            if child.node_type == "binary_expression":
                text = child.source_text.lower()
                if " and " in text or " or " in text or "&&" in text or "||" in text:
                    count += 1
        return count

    def _cognitive_score(self, node: ASTNode, depth: int) -> int:
        score = 1 if depth == 0 else 0
        for child in node.children:
            if child.node_type in self._LOOP_TYPES:
                score += 1 + (depth * 2)
                score += self._cognitive_score(child, depth + 1)
            elif child.node_type in {"if_statement", "switch_statement", "conditional_expression"}:
                score += 1 + depth
                score += self._cognitive_score(child, depth + 1)
            elif child.node_type == "binary_expression":
                text = child.source_text.lower()
                if " and " in text or " or " in text or "&&" in text or "||" in text:
                    score += 1
                    score += self._cognitive_score(child, depth + 1)
            else:
                score += self._cognitive_score(child, depth)
        return max(1, score)

    def _estimate_time(self, snippet: str, node: ASTNode) -> str:
        lower = snippet.lower()
        if "sorted(" in lower or "sort(" in lower:
            return "O(n log n)"
        if "while" in lower and any(token in lower for token in ("//= 2", ">> 1", "/= 2", "// 2")):
            return "O(log n)"
        for_count = lower.count("for")
        while_count = lower.count("while")
        if for_count >= 2 or while_count >= 2:
            return "O(n²)"
        if for_count or while_count:
            return "O(n)"
        if "recurs" in lower or "fibonacci" in lower:
            return "O(2^n)"
        if "if" in lower or "switch" in lower:
            return "O(1)"
        return "O(1)"

    def _estimate_space(self, snippet: str) -> str:
        lower = snippet.lower()
        if "[]" in lower or "list(" in lower or "append(" in lower or "copy(" in lower or "dict(" in lower or "set(" in lower:
            return "O(n)"
        if "recurs" in lower:
            return "O(n)"
        return "O(1)"

    def _maintainability(self, snippet: str, cyclomatic: int, cognitive: int) -> float:
        length = max(1, len(re.findall(r"\b\w+\b", snippet)))
        volume = max(1.0, self._halstead_volume(snippet) or 1.0)
        score = 171.0 - (5.2 * math.log(volume)) - (0.23 * cyclomatic) - (16.2 * math.log(length)) - (0.01 * cognitive)
        return max(0.0, min(100.0, score))

    def _halstead_volume(self, snippet: str) -> float:
        tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_]*|==|!=|<=|>=|&&|\|\||\+|-|\*|/|%|=|\(|\)|\{|\}|\[\]|;|:|,|\.|->", snippet)
        if not tokens:
            return 0.0
        operators = []
        operands = []
        for token in tokens:
            if token in self._HALSTEAD_OPERATORS:
                operators.append(token)
            elif token not in {"if", "for", "while", "return", "else", "switch", "case", "break", "continue"}:
                operands.append(token)
        n1 = len(set(operators))
        n2 = len(set(operands))
        N1 = len(operators)
        N2 = len(operands)
        if n1 == 0 or n2 == 0:
            return 0.0
        vocabulary = n1 + n2
        length = N1 + N2
        return length * math.log2(vocabulary) if vocabulary > 0 else 0.0

    def _risk_for(self, cyclomatic: int, cognitive: int) -> str:
        if cyclomatic >= 11 or cognitive >= 15:
            return "high"
        if cyclomatic >= 6 or cognitive >= 8:
            return "moderate"
        return "low"

    def _evidence(self, snippet: str, cyclomatic: int, cognitive: int) -> list[str]:
        evidence: list[str] = []
        if "for" in snippet.lower():
            evidence.append("Loop found in function body.")
        if "if" in snippet.lower() or "switch" in snippet.lower():
            evidence.append("Branching structure found.")
        if cyclomatic > 1:
            evidence.append(f"Cyclomatic complexity score is {cyclomatic}.")
        if cognitive > 3:
            evidence.append(f"Cognitive complexity score is {cognitive}.")
        return evidence or ["No obvious branching or loop structure detected."]


__all__ = ["ComplexityAnalyzer"]
