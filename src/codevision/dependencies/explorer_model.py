from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path

from .dependency_analyzer import DependencyAnalyzer, DependencyEdge, DependencyGraph

_HEADER_SUFFIXES = {".h", ".hh", ".hpp", ".hxx", ".inc"}
_SOURCE_SUFFIXES = {
    ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx",
    ".java", ".js", ".jsx", ".ts", ".tsx", ".py", ".rs", ".go",
    ".rb", ".php", ".swift", ".kt", ".s", ".asm",
}


@dataclass(frozen=True)
class DependencyNeighborhood:
    node_depths: dict[str, int]
    edge_indices: tuple[int, ...]
    edge_depths: dict[int, int]


@dataclass(frozen=True)
class DependencyBundle:
    bundle_id: str
    source_group: str
    target_group: str
    kind: str
    edge_indices: tuple[int, ...]


@dataclass(frozen=True)
class DependencyGroupSummary:
    group_id: str
    label: str
    node_ids: tuple[str, ...]
    incoming_count: int
    outgoing_count: int
    external_count: int


@dataclass(frozen=True)
class DependencyDirectoryNode:
    node_id: str
    relative_path: str
    display_name: str
    parent_id: str | None
    file_ids: tuple[str, ...]
    incoming_count: int = 0
    outgoing_count: int = 0

    @property
    def file_count(self) -> int:
        return len(self.file_ids)


@dataclass(frozen=True)
class DependencyDirectoryEdge:
    source_id: str
    target_id: str
    edge_indices: tuple[int, ...]

    @property
    def relationship_count(self) -> int:
        return len(self.edge_indices)


@dataclass(frozen=True)
class DependencyDirectoryProjection:
    nodes: tuple[DependencyDirectoryNode, ...]
    edges: tuple[DependencyDirectoryEdge, ...]

    @property
    def node_by_id(self) -> dict[str, DependencyDirectoryNode]:
        return {node.node_id: node for node in self.nodes}

    @property
    def edge_by_pair(self) -> dict[tuple[str, str], DependencyDirectoryEdge]:
        return {(edge.source_id, edge.target_id): edge for edge in self.edges}


class DependencyExplorerModel:
    """View-independent traversal, filtering, and visual grouping over graph records."""

    def __init__(self, graph: DependencyGraph) -> None:
        self.graph = graph
        self.node_by_id = graph.node_by_id()
        self.outgoing: dict[str, list[int]] = defaultdict(list)
        self.incoming: dict[str, list[int]] = defaultdict(list)
        for edge_index, edge in enumerate(graph.edges):
            self.outgoing[edge.source].append(edge_index)
            if edge.target in self.node_by_id:
                self.incoming[edge.target].append(edge_index)
        self._cluster_ids = self._find_clusters()
        self._cycle_edges = self._find_cycle_edges()

    def neighborhood(
        self,
        node_id: str,
        direction: str = "both",
        depth: int | None = 1,
        candidates: tuple[int, ...] | None = None,
    ) -> DependencyNeighborhood:
        if node_id not in self.node_by_id:
            return DependencyNeighborhood({}, (), {})
        if direction not in {"both", "incoming", "outgoing"}:
            raise ValueError(f"Unsupported dependency direction: {direction}")
        if depth is not None and depth < 1:
            raise ValueError("Dependency depth must be positive or None")

        node_depths = {node_id: 0}
        edge_depths: dict[int, int] = {}
        allowed_edges = None if candidates is None else set(candidates)
        pending = deque([node_id])
        while pending:
            current = pending.popleft()
            current_depth = node_depths[current]
            if depth is not None and current_depth >= depth:
                continue
            edge_indices: list[int] = []
            if direction in {"both", "outgoing"}:
                edge_indices.extend(self.outgoing.get(current, ()))
            if direction in {"both", "incoming"}:
                edge_indices.extend(self.incoming.get(current, ()))
            for edge_index in edge_indices:
                if allowed_edges is not None and edge_index not in allowed_edges:
                    continue
                edge = self.graph.edges[edge_index]
                edge_depths[edge_index] = min(
                    edge_depths.get(edge_index, current_depth + 1), current_depth + 1
                )
                neighbor = edge.target if edge.source == current else edge.source
                if neighbor in self.node_by_id and neighbor not in node_depths:
                    node_depths[neighbor] = current_depth + 1
                    pending.append(neighbor)

        return DependencyNeighborhood(
            node_depths=node_depths,
            edge_indices=tuple(sorted(edge_depths)),
            edge_depths=edge_depths,
        )

    def filter_edges(
        self,
        selected_node_id: str | None = None,
        direction: str = "all",
        kind: str = "all",
        file_type: str = "all",
        cycles_only: bool = False,
        candidates: tuple[int, ...] | None = None,
    ) -> tuple[int, ...]:
        if direction not in {"all", "incoming", "outgoing"}:
            raise ValueError(f"Unsupported dependency direction: {direction}")
        if kind not in {"all", "internal", "external", "stdlib", "unresolved"}:
            raise ValueError(f"Unsupported dependency kind: {kind}")
        if file_type not in {"all", "header", "source"}:
            raise ValueError(f"Unsupported dependency file type: {file_type}")

        selected = range(len(self.graph.edges)) if candidates is None else candidates
        matching = []
        for edge_index in selected:
            edge = self.graph.edges[edge_index]
            if kind != "all" and edge.kind != kind:
                continue
            if direction == "incoming" and (selected_node_id is None or edge.target != selected_node_id):
                continue
            if direction == "outgoing" and (selected_node_id is None or edge.source != selected_node_id):
                continue
            if cycles_only and edge_index not in self._cycle_edges:
                continue
            if file_type != "all" and not self._matches_file_type(edge, file_type):
                continue
            matching.append(edge_index)
        return tuple(matching)

    def bundle_edges(
        self,
        grouping: str = "directory",
        edge_indices: tuple[int, ...] | None = None,
    ) -> tuple[DependencyBundle, ...]:
        if grouping not in {"directory", "module", "file-type", "cluster"}:
            raise ValueError(f"Unsupported dependency grouping: {grouping}")
        selected = range(len(self.graph.edges)) if edge_indices is None else edge_indices
        buckets: dict[tuple[str, str, str], list[int]] = defaultdict(list)
        for edge_index in selected:
            edge = self.graph.edges[edge_index]
            source_group = self.group_for_node(edge.source, grouping)
            target_group = self.group_for_node(edge.target, grouping, edge.kind)
            buckets[(source_group, target_group, edge.kind)].append(edge_index)
        return tuple(
            DependencyBundle(
                bundle_id=f"{source}\0{target}\0{kind}",
                source_group=source,
                target_group=target,
                kind=kind,
                edge_indices=tuple(indices),
            )
            for (source, target, kind), indices in sorted(buckets.items())
        )

    def groups(self, grouping: str = "directory") -> tuple[DependencyGroupSummary, ...]:
        grouped_nodes: dict[str, list[str]] = defaultdict(list)
        for node_id in self.node_by_id:
            grouped_nodes[self.group_for_node(node_id, grouping)].append(node_id)
        incoming = defaultdict(int)
        outgoing = defaultdict(int)
        external = defaultdict(int)
        for edge in self.graph.edges:
            source_group = self.group_for_node(edge.source, grouping)
            outgoing[source_group] += 1
            if edge.target in self.node_by_id:
                incoming[self.group_for_node(edge.target, grouping)] += 1
            else:
                external[source_group] += 1
        return tuple(
            DependencyGroupSummary(
                group_id=group_id,
                label=group_id,
                node_ids=tuple(sorted(node_ids)),
                incoming_count=incoming[group_id],
                outgoing_count=outgoing[group_id],
                external_count=external[group_id],
            )
            for group_id, node_ids in sorted(grouped_nodes.items())
        )

    def directory_projection(
        self,
        project_root: str | Path,
        edge_indices: tuple[int, ...] | None = None,
        directories: tuple[Path, ...] | None = None,
    ) -> DependencyDirectoryProjection:
        root = Path(project_root).expanduser().resolve()
        if root.is_file():
            root = root.parent
        directory_paths = directories or tuple(DependencyAnalyzer._discover_directories(root))
        file_ids_by_directory: dict[str, list[str]] = defaultdict(list)
        relative_by_id: dict[str, str] = {}
        for node in self.graph.nodes:
            relative = Path(node.relative_path).as_posix()
            directory_id = Path(relative).parent.as_posix()
            directory_id = "." if directory_id == "." else directory_id
            file_ids_by_directory[directory_id].append(node.node_id)
            relative_by_id[node.node_id] = relative

        directory_ids: set[str] = set()
        for path in directory_paths:
            relative = path.relative_to(root).as_posix()
            directory_ids.add("." if relative == "." else relative)
        directory_ids.update(file_ids_by_directory)

        child_directories: dict[str, list[str]] = defaultdict(list)
        for directory_id in directory_ids:
            if directory_id == ".":
                continue
            parent_id = Path(directory_id).parent.as_posix()
            parent_id = "." if parent_id == "." else parent_id
            if parent_id in directory_ids:
                child_directories[parent_id].append(directory_id)
        recursive_files: dict[str, tuple[str, ...]] = {}

        def files_under(directory_id: str) -> tuple[str, ...]:
            if directory_id not in recursive_files:
                files = list(file_ids_by_directory.get(directory_id, ()))
                for child_id in child_directories.get(directory_id, ()):
                    files.extend(files_under(child_id))
                recursive_files[directory_id] = tuple(sorted(set(files)))
            return recursive_files[directory_id]

        edge_buckets: dict[tuple[str, str], list[int]] = defaultdict(list)
        selected_edges = range(len(self.graph.edges)) if edge_indices is None else edge_indices
        for edge_index in selected_edges:
            edge = self.graph.edges[edge_index]
            if edge.source not in relative_by_id or edge.target not in relative_by_id:
                continue
            source_directory = Path(relative_by_id[edge.source]).parent.as_posix()
            target_directory = Path(relative_by_id[edge.target]).parent.as_posix()
            source_directory = "." if source_directory == "." else source_directory
            target_directory = "." if target_directory == "." else target_directory
            if source_directory == target_directory:
                continue
            edge_buckets[(source_directory, target_directory)].append(edge_index)

        incoming = defaultdict(int)
        outgoing = defaultdict(int)
        projected_edges = []
        for (source_id, target_id), indices in sorted(edge_buckets.items()):
            projected_edges.append(
                DependencyDirectoryEdge(source_id, target_id, tuple(indices))
            )
            outgoing[source_id] += len(indices)
            incoming[target_id] += len(indices)

        nodes = []
        for directory_id in sorted(directory_ids):
            path = Path(directory_id)
            display_name = root.name if directory_id == "." else path.name
            parent_id = None if directory_id == "." else path.parent.as_posix()
            if parent_id == "." or parent_id == "":
                parent_id = "."
            nodes.append(
                DependencyDirectoryNode(
                    node_id=directory_id,
                    relative_path=directory_id,
                    display_name=display_name,
                    parent_id=parent_id,
                    file_ids=files_under(directory_id),
                    incoming_count=incoming[directory_id],
                    outgoing_count=outgoing[directory_id],
                )
            )
        return DependencyDirectoryProjection(tuple(nodes), tuple(projected_edges))

    def group_for_node(
        self, node_id: str, grouping: str = "directory", edge_kind: str = "external"
    ) -> str:
        node = self.node_by_id.get(node_id)
        if node is None:
            return f"{edge_kind}: {node_id}"
        path = Path(node.relative_path)
        if grouping == "directory":
            parent = path.parent.as_posix()
            return "." if parent == "." else parent
        if grouping == "module":
            return path.parts[0] if len(path.parts) > 1 else path.stem
        if grouping == "file-type":
            suffix = path.suffix.lower()
            if suffix in _HEADER_SUFFIXES:
                return "Headers"
            if suffix in _SOURCE_SUFFIXES:
                return "Sources"
            return "Other files"
        if grouping == "cluster":
            return self._cluster_ids.get(node_id, f"Cluster: {node_id}")
        raise ValueError(f"Unsupported dependency grouping: {grouping}")

    def relationship(self, query: str) -> tuple[int, ...]:
        query = query.replace("→", "->")
        source_query, separator, target_query = query.partition("->")
        if not separator:
            return ()
        source_query = source_query.strip().casefold()
        target_query = target_query.strip().casefold()
        matches = []
        for index, edge in enumerate(self.graph.edges):
            source = self._node_label(edge.source).casefold()
            target = self._node_label(edge.target).casefold()
            if source_query in source and target_query in target:
                matches.append(index)
        return tuple(matches)

    def node_counts(self, node_id: str) -> dict[str, int | bool]:
        outgoing = self.outgoing.get(node_id, ())
        incoming = self.incoming.get(node_id, ())
        outgoing_external = sum(
            self.graph.edges[index].target not in self.node_by_id for index in outgoing
        )
        reachable = self.neighborhood(node_id, direction="outgoing", depth=None)
        return {
            "direct_dependencies": len(outgoing),
            "incoming_dependencies": len(incoming),
            "outgoing_dependencies": len(outgoing),
            "transitive_dependencies": max(0, len(reachable.node_depths) - 1),
            "external_dependencies": outgoing_external,
            "circular": any(node_id in cycle for cycle in self.graph.cycles),
        }

    def _find_clusters(self) -> dict[str, str]:
        parent = {node_id: node_id for node_id in self.node_by_id}

        def find(node_id: str) -> str:
            while parent[node_id] != node_id:
                parent[node_id] = parent[parent[node_id]]
                node_id = parent[node_id]
            return node_id

        for edge in self.graph.edges:
            if edge.target not in parent:
                continue
            source_root = find(edge.source)
            target_root = find(edge.target)
            if source_root != target_root:
                first, second = sorted((source_root, target_root))
                parent[second] = first
        roots = sorted({find(node_id) for node_id in parent})
        labels = {root: f"Cluster {index + 1}" for index, root in enumerate(roots)}
        return {node_id: labels[find(node_id)] for node_id in parent}

    def _find_cycle_edges(self) -> set[int]:
        cycle_pairs: set[tuple[str, str]] = set()
        for cycle in self.graph.cycles:
            cycle_pairs.update(zip(cycle, cycle[1:]))
            if len(cycle) > 1:
                cycle_pairs.add((cycle[-1], cycle[0]))
        return {
            index
            for index, edge in enumerate(self.graph.edges)
            if (edge.source, edge.target) in cycle_pairs
        }

    def _matches_file_type(self, edge: DependencyEdge, file_type: str) -> bool:
        target = self.node_by_id.get(edge.target)
        suffix = (
            Path(target.relative_path).suffix.lower()
            if target is not None
            else Path(edge.import_name).suffix.lower()
        )
        if file_type == "header":
            return suffix in _HEADER_SUFFIXES
        return suffix in _SOURCE_SUFFIXES and suffix not in _HEADER_SUFFIXES

    def _node_label(self, node_id: str) -> str:
        node = self.node_by_id.get(node_id)
        return node.relative_path if node is not None else node_id


__all__ = [
    "DependencyBundle",
    "DependencyDirectoryEdge",
    "DependencyDirectoryNode",
    "DependencyDirectoryProjection",
    "DependencyExplorerModel",
    "DependencyGroupSummary",
    "DependencyNeighborhood",
]
