from __future__ import annotations

import re
import sys
import os
from dataclasses import dataclass, field
from pathlib import Path

_CODE_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".c",
    ".cc",
    ".cpp",
    ".cxx",
    ".h",
    ".hh",
    ".hpp",
    ".java",
    ".cs",
    ".rs",
    ".go",
    ".rb",
    ".php",
    ".swift",
    ".kt",
    ".s",
    ".asm",
}

_SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    "site-packages",
}

_PYTHON_IMPORT_RE = re.compile(
    r"^\s*(?:from\s+([\.\w]+)\s+import\s+.+|import\s+([\.\w]+))",
    re.MULTILINE,
)

_JS_IMPORT_RE = re.compile(
    r"(?:import|export)\s+(?:[^;]*?\s+from\s+)?['\"]([^'\"]+)['\"]|require\(['\"]([^'\"]+)['\"]\)",
    re.MULTILINE,
)

_CPP_INCLUDE_RE = re.compile(r"^\s*#\s*include\s*[<\"]([^>\"]+)[>\"]", re.MULTILINE)


@dataclass(frozen=True)
class DependencyNode:
    node_id: str
    relative_path: str
    display_name: str
    module_name: str | None
    file_path: Path


@dataclass(frozen=True)
class DependencyEdge:
    source: str
    target: str
    kind: str
    import_name: str
    line: int = 0


@dataclass
class DependencyGraph:
    nodes: list[DependencyNode]
    edges: list[DependencyEdge] = field(default_factory=list)
    cycles: list[list[str]] = field(default_factory=list)

    def node_by_id(self) -> dict[str, DependencyNode]:
        return {node.node_id: node for node in self.nodes}


@dataclass
class DependencyReport:
    project_root: Path
    graph: DependencyGraph
    summary: dict[str, int | str]


class DependencyAnalyzer:
    """Build a project-level dependency graph from source files on disk."""

    def analyze(self, project_root: str | Path | None) -> DependencyReport:
        root = Path(project_root).expanduser().resolve() if project_root is not None else Path.cwd()
        if not root.exists():
            raise FileNotFoundError(f"Dependency analysis requires an existing project directory: {root}")
        if root.is_file():
            root = root.parent

        files = self._discover_files(root)
        nodes = [
            DependencyNode(
                node_id=self._relative_key(file_path.relative_to(root)),
                relative_path=self._relative_key(file_path.relative_to(root)),
                display_name=file_path.name,
                module_name=self._module_name(file_path, root),
                file_path=file_path,
            )
            for file_path in files
        ]
        node_map = {node.node_id: node for node in nodes}
        edges: list[DependencyEdge] = []
        adjacency: dict[str, set[str]] = {node.node_id: set() for node in nodes}

        for file_path in sorted(files):
            source_id = self._relative_key(file_path.relative_to(root))
            try:
                contents = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                contents = file_path.read_text(encoding="utf-8", errors="replace")

            for import_name, line_number in self._scan_imports(file_path, contents):
                target_id = self._resolve_import(file_path, root, import_name)
                if target_id == source_id:
                    continue
                if target_id is None:
                    top_level_import = import_name.lstrip(".").split(".", 1)[0]
                    if top_level_import in sys.stdlib_module_names:
                        kind = "stdlib"
                    elif import_name.startswith((".", "/", "./", "../")) or "/" in import_name:
                        kind = "unresolved"
                    else:
                        kind = "external"
                    target_label = import_name
                else:
                    kind = self._classify_kind(import_name, source_id, target_id, root)
                    if target_id in adjacency:
                        adjacency[source_id].add(target_id)
                    target_label = target_id

                edge = DependencyEdge(
                    source=source_id,
                    target=target_label if target_id is None else target_id,
                    kind=kind,
                    import_name=import_name,
                    line=line_number,
                )
                if edge not in edges:
                    edges.append(edge)

        cycles = self._detect_cycles(adjacency)
        graph = DependencyGraph(nodes=sorted(nodes, key=lambda item: item.relative_path), edges=sorted(edges, key=lambda item: (item.source, item.target, item.kind)), cycles=cycles)
        summary = {
            "total_files": len(nodes),
            "total_edges": len(edges),
            "internal_edges": sum(1 for edge in edges if edge.kind == "internal"),
            "stdlib_edges": sum(1 for edge in edges if edge.kind == "stdlib"),
            "external_edges": sum(1 for edge in edges if edge.kind == "external"),
            "unresolved_edges": sum(1 for edge in edges if edge.kind == "unresolved"),
            "cycle_count": len(cycles),
            "files_with_dependencies": len({edge.source for edge in edges}),
            "project_root": str(root),
        }
        return DependencyReport(project_root=root, graph=graph, summary=summary)

    @staticmethod
    def _discover_files(root: Path) -> list[Path]:
        found: list[Path] = []
        for directory, child_dirs, file_names in os.walk(root):
            child_dirs[:] = sorted(
                name for name in child_dirs if name not in _SKIP_DIRS
            )
            for file_name in file_names:
                path = Path(directory) / file_name
                if path.suffix.lower() in _CODE_EXTENSIONS:
                    found.append(path)
        return sorted(found)

    @staticmethod
    def _discover_directories(root: Path) -> list[Path]:
        found = [root]
        for directory, child_dirs, _file_names in os.walk(root):
            child_dirs[:] = sorted(
                name for name in child_dirs if name not in _SKIP_DIRS
            )
            found.extend(Path(directory) / name for name in child_dirs)
        return sorted(set(found), key=lambda path: path.relative_to(root).as_posix())

    @staticmethod
    def _relative_key(path: Path) -> str:
        return path.as_posix()

    def _module_name(self, file_path: Path, root: Path) -> str | None:
        rel = file_path.relative_to(root)
        if rel.name == "__init__.py":
            if rel.parent == Path("."):
                return "__init__"
            return ".".join(rel.parent.parts)
        stem = rel.with_suffix("")
        if stem == Path("."):
            return None
        return ".".join(stem.parts)

    def _scan_imports(self, file_path: Path, contents: str) -> list[tuple[str, int]]:
        suffix = file_path.suffix.lower()
        if suffix == ".py":
            matches = []
            for match in _PYTHON_IMPORT_RE.finditer(contents):
                imported = match.group(1) or match.group(2)
                if imported is None:
                    continue
                line_number = contents[: match.start()].count("\n") + 1
                matches.append((imported, line_number))
            return matches
        if suffix in {".js", ".jsx", ".ts", ".tsx"}:
            matches = []
            for match in _JS_IMPORT_RE.finditer(contents):
                import_name = match.group(1) or match.group(2)
                if import_name is None:
                    continue
                line_number = contents[: match.start()].count("\n") + 1
                matches.append((import_name, line_number))
            return matches
        if suffix in {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp"}:
            matches = []
            for match in _CPP_INCLUDE_RE.finditer(contents):
                include_name = match.group(1)
                line_number = contents[: match.start()].count("\n") + 1
                matches.append((include_name, line_number))
            return matches
        return []

    def _resolve_import(self, file_path: Path, root: Path, import_name: str) -> str | None:
        if file_path.suffix.lower() == ".py" and import_name.startswith("."):
            relative_level = len(import_name) - len(import_name.lstrip("."))
            module_name = import_name[relative_level:]
            base_directory = file_path.parent
            for _ in range(relative_level - 1):
                base_directory = base_directory.parent
            candidate = base_directory.joinpath(*module_name.split("."))
            candidates = [candidate]
            if candidate.is_dir():
                candidates.append(candidate / "__init__.py")
            for extension in (".py", ".js", ".ts", ".tsx", ".jsx"):
                candidates.append(Path(str(candidate) + extension))
            for test_path in candidates:
                try:
                    if test_path.is_file() and test_path.resolve().is_relative_to(root):
                        return self._relative_key(test_path.resolve().relative_to(root))
                except ValueError:
                    continue
            return None

        if import_name.startswith(".") or import_name.startswith("/") or "/" in import_name:
            if import_name.startswith("/"):
                candidate = Path(import_name).resolve()
            else:
                candidate = (file_path.parent / import_name).resolve()
            for extension in ("", ".py", ".js", ".ts", ".tsx", ".jsx", ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".s", ".asm"):
                test_path = candidate if extension == "" else Path(str(candidate) + extension)
                try:
                    if test_path.exists() and test_path.is_relative_to(root):
                        return self._relative_key(test_path.relative_to(root))
                except ValueError:
                    continue
            return None

        import_parts = [part for part in import_name.split(".") if part]
        candidate_paths: list[Path] = []
        if import_parts:
            import_roots = [root] + [
                root / name
                for name in ("src", "lib", "python")
                if (root / name).is_dir()
            ]
            for import_root in import_roots:
                candidate_paths.append(import_root.joinpath(*import_parts))
                if len(import_parts) > 1:
                    candidate_paths.append(import_root.joinpath(*import_parts[1:]))
                    candidate_paths.append(import_root / import_parts[-1])
        candidate_paths.append(root / import_name)
        for candidate in candidate_paths:
            if candidate.is_dir():
                if (candidate / "__init__.py").exists():
                    return self._relative_key((candidate / "__init__.py").relative_to(root))
            for extension in ("", ".py", ".js", ".ts", ".tsx", ".jsx", ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp"):
                test_path = candidate if extension == "" else Path(str(candidate) + extension)
                if test_path.exists() and test_path.is_relative_to(root):
                    return self._relative_key(test_path.relative_to(root))

        if file_path.parent != root:
            base_dir = file_path.parent
            for extension in ("", ".py", ".js", ".ts", ".tsx", ".jsx", ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp"):
                test_path = base_dir / import_name
                if extension:
                    test_path = Path(str(test_path) + extension)
                if test_path.exists() and test_path.is_relative_to(root):
                    return self._relative_key(test_path.relative_to(root))

        return None

    @staticmethod
    def _classify_kind(import_name: str, source_id: str, target_id: str, root: Path) -> str:
        if import_name in set(sys.stdlib_module_names):
            return "stdlib"
        if import_name.startswith(".") or (source_id != target_id and target_id and target_id.endswith(".py") and source_id.split("/")[0] == target_id.split("/")[0]):
            return "internal"
        if source_id != target_id and Path(root / target_id).exists():
            return "internal"
        if import_name.startswith("./") or import_name.startswith("../"):
            return "internal"
        return "external"

    @staticmethod
    def _detect_cycles(adjacency: dict[str, set[str]]) -> list[list[str]]:
        visited: set[str] = set()
        stack: list[str] = []
        cycles: list[list[str]] = []

        def dfs(node_id: str) -> None:
            visited.add(node_id)
            stack.append(node_id)
            for neighbor in adjacency.get(node_id, set()):
                if neighbor not in visited:
                    dfs(neighbor)
                elif neighbor in stack:
                    cycle = stack[stack.index(neighbor):] + [neighbor]
                    cycle = list(dict.fromkeys(cycle))
                    if cycle and cycle not in cycles:
                        cycles.append(cycle)
            stack.pop()

        for node_id in sorted(adjacency):
            if node_id not in visited:
                dfs(node_id)
        return cycles
