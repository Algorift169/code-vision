from __future__ import annotations

import math
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from ...dependencies import DependencyAnalyzer, DependencyBundle, DependencyExplorerModel


@dataclass
class _Node:
    node_id: str
    label: str
    detail: str
    kind: str
    x: float
    y: float
    file_path: Path | None = None
    group_id: str | None = None
    members: tuple[str, ...] = ()
    is_group: bool = False
    dimmed: bool = False
    selected: bool = False
    outgoing_target: bool = False
    is_directory: bool = False
    file_count: int = 0


@dataclass(frozen=True)
class _Edge:
    source: str
    target: str
    kind: str
    indices: tuple[int, ...]
    bundle_id: str | None = None
    bundle_summary: bool = False
    incoming: bool = False
    depth: int = 1


class DependencyView(Gtk.Box):
    """Progressively disclosed, project-wide dependency graph workspace."""

    NODE_WIDTH = 236.0
    NODE_HEIGHT = 78.0
    _MAX_OVERVIEW_BUNDLES = 120

    def __init__(self, on_file_navigate: Callable[[Path], None] | None = None) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_hexpand(True)
        self.set_vexpand(True)
        self._on_file_navigate = on_file_navigate
        self._project_root: Path | None = None
        self._analysis = None
        self._model: DependencyExplorerModel | None = None
        self._directory_projection = None
        self._directory_paths: tuple[Path, ...] = ()
        self._view_kind = "all"
        self._picked_item: tuple[str, str] | None = None
        self._pre_pick_mode: tuple[str, str | None] | None = None
        self._pre_pick_view: str | None = None
        self._selected_directory: str | None = None
        self._collapsed_directories: set[str] = set()
        self._directory_positions: dict[str, tuple[float, float]] = {}
        self._mode = "overview"
        self._grouping = "directory"
        self._selected_node: str | None = None
        self._all_nodes_selected = False
        self._selected_sources: set[str] = set()
        self._expanded_groups: set[str] = set()
        self._expanded_bundles: set[str] = set()
        self._collapsed_bundles: set[str] = set()
        self._focus_edges: set[int] = set()
        self._zoom = 1.0
        self._pan = (0.0, 0.0)
        self._drag_origin = (0.0, 0.0)
        self._groups: dict[str, object] = {}
        self._external_group_counts: dict[str, int] = {}
        self._cycle_indices: set[int] = set()
        self._detail_group_id: str | None = None
        self._detail_directory_id: str | None = None
        self._group_ids: set[str] = set()
        self._group_positions: dict[str, tuple[float, float]] = {}
        self._file_positions: dict[str, tuple[float, float]] = {}
        self._nodes: list[_Node] = []
        self._node_by_id: dict[str, _Node] = {}
        self._edges: list[_Edge] = []
        self._routes: list[tuple[tuple[float, float], ...]] = []
        self._hover_edge: int | None = None
        self._updating_controls = False
        self._node_grid: dict[tuple[int, int], list[int]] = defaultdict(list)
        self._edge_grid: dict[tuple[int, int], list[int]] = defaultdict(list)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.title = Gtk.Label(label="Dependency")
        self.title.add_css_class("analysis-placeholder-title")
        self.title.set_halign(Gtk.Align.START)
        self.title.set_hexpand(True)
        header.append(self.title)
        self.status = Gtk.Label(label="Overview")
        self.status.set_halign(Gtk.Align.END)
        self.status.set_ellipsize(3)
        header.append(self.status)
        self.append(header)

        self.view_select = self._dropdown(["All", "Only Directories"])
        self.view_select.set_selected(0)
        self.view_select.set_size_request(140, -1)
        self.view_select.set_tooltip_text("Choose file-level or directory-level dependency view")
        self.view_select.connect("notify::selected", self._on_view_changed)
        self.pick_menu = Gtk.MenuButton()
        self.pick_menu.set_child(Gtk.Label(label="PICK"))
        self.pick_menu.add_css_class("theme-toolbar-button")
        self.pick_menu.set_tooltip_text("Select a file or directory to inspect")
        self.pick_popover = Gtk.Popover()
        self.pick_popover.add_css_class("theme-picker-popover")
        picker_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        picker_content.add_css_class("theme-picker-content")
        picker_content.set_size_request(320, 420)
        picker_title = Gtk.Label(label="Pick a file or directory")
        picker_title.set_halign(Gtk.Align.START)
        picker_content.append(picker_title)
        self.pick_search = Gtk.SearchEntry()
        self.pick_search.set_placeholder_text("Search filename or relative path")
        self.pick_search.connect("changed", self._on_pick_search_changed)
        picker_content.append(self.pick_search)
        picker_scroll = Gtk.ScrolledWindow()
        picker_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        picker_scroll.set_min_content_height(300)
        self.pick_results = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        picker_scroll.set_child(self.pick_results)
        picker_content.append(picker_scroll)
        self.pick_popover.set_child(picker_content)
        self.pick_menu.set_popover(self.pick_popover)
        self.picked_label = Gtk.Label(label="No selection")
        self.picked_label.set_ellipsize(3)
        self.picked_label.set_max_width_chars(18)
        self.clear_pick_button = Gtk.Button.new_from_icon_name("edit-clear-symbolic")
        self.clear_pick_button.add_css_class("theme-toolbar-button")
        self.clear_pick_button.set_tooltip_text("Clear picked file or directory")
        self.clear_pick_button.connect("clicked", self._on_clear_pick)
        self.clear_pick_button.set_sensitive(False)

        self.mode_select = self._dropdown(["Overview", "Explore selection", "Full map"])
        self.mode_select.set_tooltip_text("Choose overview, node exploration, or the full bundled map")
        self.mode_select.connect("notify::selected", self._on_mode_changed)
        self.group_select = self._dropdown(["Directory", "Module", "File type", "Dependency cluster"])
        self.group_select.set_tooltip_text("Group files by directory, module, file type, or connected cluster")
        self.group_select.connect("notify::selected", self._on_group_changed)
        refresh = Gtk.Button.new_from_icon_name("view-refresh-symbolic")
        refresh.add_css_class("theme-toolbar-button")
        refresh.set_tooltip_text("Reanalyze project")
        refresh.connect("clicked", lambda _button: self.set_project_root(self._project_root, force=True))
        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        top.append(self.view_select)
        top.append(self.pick_menu)
        top.append(self.picked_label)
        top.append(self.clear_pick_button)
        self.append(top)
        graph_controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        graph_controls.append(self.mode_select)
        graph_controls.append(self.group_select)
        graph_controls.append(refresh)
        self.append(graph_controls)

        self.search = Gtk.SearchEntry()
        self.search.set_placeholder_text("Find relationship: source -> target")
        self.search.connect("activate", self._on_search)
        self.append(self.search)

        self.direction = self._dropdown(["Both directions", "Outgoing", "Incoming"])
        self.direction.set_tooltip_text("Explore incoming or outgoing relationships from the selected file")
        self.direction.connect("notify::selected", self._on_filters_changed)
        self.kind = self._dropdown(["All types", "Internal", "External", "Standard library", "Unresolved"])
        self.kind.set_tooltip_text("Filter by dependency type")
        self.kind.connect("notify::selected", self._on_filters_changed)
        filters = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        filters.append(self.direction)
        filters.append(self.kind)
        self.append(filters)

        self.file_type = self._dropdown(["All files", "Header dependencies", "Source dependencies"])
        self.file_type.set_tooltip_text("Filter header or source dependencies")
        self.file_type.connect("notify::selected", self._on_filters_changed)
        self.depth = self._dropdown(["Depth 1", "Depth 2", "Depth 3", "All reachable"])
        self.depth.set_tooltip_text("Set dependency exploration depth")
        self.depth.connect("notify::selected", self._on_filters_changed)
        self.cycles = Gtk.ToggleButton(label="Cycles only")
        self.cycles.connect("toggled", self._on_filters_changed)
        reset = Gtk.Button.new_from_icon_name("edit-clear-symbolic")
        reset.add_css_class("theme-toolbar-button")
        reset.set_tooltip_text("Reset filters and selection")
        reset.connect("clicked", self._on_reset)
        filters = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        filters.append(self.file_type)
        filters.append(self.depth)
        filters.append(self.cycles)
        filters.append(reset)
        self.append(filters)

        self.metrics = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.metrics.set_hexpand(True)
        self.append(self.metrics)

        self.canvas = Gtk.DrawingArea()
        self.canvas.set_name("dependency-graph-canvas")
        self.canvas.set_hexpand(True)
        self.canvas.set_vexpand(True)
        self.canvas.set_content_width(1)
        self.canvas.set_content_height(300)
        self.canvas.set_draw_func(self._draw)
        click = Gtk.GestureClick.new()
        click.connect("pressed", self._on_click)
        self.canvas.add_controller(click)
        drag = Gtk.GestureDrag.new()
        drag.connect("drag-begin", self._on_pan_begin)
        drag.connect("drag-update", self._on_pan_update)
        self.canvas.add_controller(drag)
        motion = Gtk.EventControllerMotion.new()
        motion.connect("motion", self._on_motion)
        self.canvas.add_controller(motion)
        self.scroller = Gtk.ScrolledWindow()
        self.scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.scroller.set_hexpand(True)
        self.scroller.set_vexpand(True)
        self.scroller.set_child(self.canvas)
        self.empty = Gtk.Label(label="Open a project folder to inspect dependencies.")
        self.empty.set_wrap(True)
        self.empty.set_halign(Gtk.Align.CENTER)
        self.empty.set_valign(Gtk.Align.CENTER)
        self.scroller.set_child(self.empty)
        self.append(self.scroller)

        self.details_title = Gtk.Label(label="Dependency details")
        self.details_title.add_css_class("complexity-panel-title")
        self.details_title.set_halign(Gtk.Align.START)
        self.append(self.details_title)
        self.details = Gtk.Label(label="Select a directory group or file to inspect its relationships.")
        self.details.set_halign(Gtk.Align.START)
        self.details.set_wrap(True)
        self.append(self.details)
        self.detail_search = Gtk.SearchEntry()
        self.detail_search.set_placeholder_text("Filter files in this group")
        self.detail_search.set_visible(False)
        self.detail_search.connect("changed", self._on_group_file_search)
        self.append(self.detail_search)
        self.details_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.details_scroll = Gtk.ScrolledWindow()
        self.details_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.details_scroll.set_max_content_height(116)
        self.details_scroll.set_child(self.details_list)
        self.append(self.details_scroll)

    @staticmethod
    def _dropdown(options: list[str]) -> Gtk.DropDown:
        control = Gtk.DropDown.new_from_strings(options)
        control.set_hexpand(True)
        return control

    def set_project_root(self, root: Path | None, force: bool = False) -> None:
        root = root.resolve() if root is not None else None
        if not force and root == self._project_root and self._model is not None:
            return
        self._project_root = root
        if root is None:
            self._analysis = self._model = None
            self._show_empty("Open a project folder to inspect dependencies.")
            return
        try:
            self._analysis = DependencyAnalyzer().analyze(root)
            self._model = DependencyExplorerModel(self._analysis.graph)
            self._directory_paths = tuple(DependencyAnalyzer._discover_directories(root))
            self._directory_projection = self._model.directory_projection(
                root, directories=self._directory_paths
            )
        except (OSError, ValueError) as error:
            self._analysis = self._model = None
            self._show_empty(f"Dependency graph unavailable: {error}")
            return
        self._selected_node = None
        self._all_nodes_selected = False
        self._picked_item = None
        self._selected_directory = None
        self._pre_pick_mode = None
        self._pre_pick_view = None
        self._expanded_groups.clear()
        self._expanded_bundles.clear()
        self._focus_edges.clear()
        self._populate_pick_results()
        self._prepare_layout()
        self._render()

    def _show_empty(self, text: str) -> None:
        self.empty.set_text(text)
        self.scroller.set_child(self.empty)
        self._nodes.clear()
        self._edges.clear()
        self._node_by_id.clear()
        self._refresh_metrics()

    def _prepare_layout(self) -> None:
        model = self._model
        self._groups = {item.group_id: item for item in model.groups(self._grouping)}
        self._cycle_indices = set(model.filter_edges(cycles_only=True))
        all_bundles = model.bundle_edges(self._grouping)
        self._group_ids = set(self._groups)
        self._external_group_counts = defaultdict(int)
        for edge in model.graph.edges:
            if edge.target not in model.node_by_id:
                target_group = model.group_for_node(edge.target, self._grouping, edge.kind)
                self._external_group_counts[target_group] += 1
        for bundle in all_bundles:
            self._group_ids.update((bundle.source_group, bundle.target_group))
        outgoing: dict[str, set[str]] = defaultdict(set)
        incoming = {item: 0 for item in self._group_ids}
        for bundle in all_bundles:
            if bundle.source_group != bundle.target_group:
                outgoing[bundle.source_group].add(bundle.target_group)
                incoming[bundle.target_group] += 1
        rank = {key: 0 for key, count in incoming.items() if count == 0}
        pending = deque(sorted(rank))
        while pending:
            source = pending.popleft()
            for target in sorted(outgoing[source]):
                candidate = min(rank[source] + 1, 5)
                if candidate > rank.get(target, -1):
                    rank[target] = candidate
                    pending.append(target)
        for key in self._group_ids:
            rank.setdefault(key, 0)
        columns: dict[int, list[str]] = defaultdict(list)
        for key in self._group_ids:
            columns[rank[key]].append(key)
        self._group_positions = {}
        self._file_positions = {}
        for column, groups in sorted(columns.items()):
            y = 40.0
            for group_id in sorted(groups):
                group = self._groups.get(group_id)
                self._group_positions[group_id] = (48.0 + column * 350.0, y)
                if group is not None:
                    for row, node_id in enumerate(group.node_ids):
                        self._file_positions[node_id] = (
                            48.0 + column * 350.0,
                            y + 100.0 + row * 88.0,
                        )
                    y += max(138.0, 116.0 + len(group.node_ids) * 88.0)
                else:
                    y += 138.0
        self._prepare_directory_layout()

    def _prepare_directory_layout(self) -> None:
        if self._directory_projection is None:
            self._directory_positions = {}
            return
        node_by_id = self._directory_projection.node_by_id
        children: dict[str, list[str]] = defaultdict(list)
        for node in self._directory_projection.nodes:
            if node.parent_id is not None and node.parent_id in node_by_id:
                children[node.parent_id].append(node.node_id)
        positions: dict[str, tuple[float, float]] = {}
        next_row = 0

        def place(directory_id: str, depth: int) -> float:
            nonlocal next_row
            child_positions = [
                place(child_id, depth + 1)
                for child_id in sorted(children[directory_id])
            ]
            if child_positions:
                y = (child_positions[0] + child_positions[-1]) / 2
            else:
                y = 44.0 + next_row * 112.0
                next_row += 1
            positions[directory_id] = (48.0 + depth * 350.0, y)
            return y

        if "." in node_by_id:
            place(".", 0)
        for directory_id in sorted(set(node_by_id) - set(positions)):
            place(directory_id, len(Path(directory_id).parts))
        self._directory_positions = positions

    def _render(self) -> None:
        if self._model is None:
            return
        self._nodes = []
        self._edges = []
        self._node_by_id = {}
        self._selected_sources = set()
        candidates = self._model.filter_edges(
            kind=("all", "internal", "external", "stdlib", "unresolved")[self.kind.get_selected()],
            file_type=("all", "header", "source")[self.file_type.get_selected()],
            cycles_only=self.cycles.get_active(),
        )
        if self._view_kind == "directories":
            self._build_directory_view(candidates)
        elif self._picked_item == ("directory", self._selected_directory):
            self._build_directory_file_explore(candidates)
        elif self._mode == "explore" and self._selected_node:
            self._build_explore(candidates)
        elif self._mode == "full":
            self._build_full(candidates)
        else:
            self._build_overview(candidates)
        if not self._nodes:
            self._show_empty("No project files or relationships match these filters.")
            return
        self.scroller.set_child(self.canvas)
        self._cache_geometry()
        self._refresh_metrics()
        self.canvas.set_content_width(max(320, math.ceil((max(n.x for n in self._nodes) + self.NODE_WIDTH + 80) * self._zoom)))
        self.canvas.set_content_height(max(280, math.ceil((max(n.y for n in self._nodes) + self.NODE_HEIGHT + 80) * self._zoom)))
        self.canvas.queue_draw()

    def _build_directory_view(self, candidates: tuple[int, ...]) -> None:
        root = self._project_root
        projection = self._directory_projection
        if root is None or projection is None:
            return
        visible_ids = set()
        for directory in projection.nodes:
            current = directory.node_id
            hidden = False
            while current != ".":
                parent = projection.node_by_id[current].parent_id
                if parent is None:
                    break
                if parent in self._collapsed_directories:
                    hidden = True
                    break
                current = parent
            if not hidden:
                visible_ids.add(directory.node_id)

        def visible_ancestor(directory_id: str) -> str | None:
            current: str | None = directory_id
            while current is not None and current not in visible_ids:
                current = projection.node_by_id[current].parent_id
            return current

        selected = self._selected_directory if self._picked_item is not None else None

        def selected_scope(directory_id: str) -> str:
            if selected is not None and (
                directory_id == selected
                or directory_id.startswith(selected.rstrip(".") + "/")
            ):
                return selected
            return directory_id

        filtered_projection = self._model.directory_projection(
            root, edge_indices=candidates, directories=self._directory_paths
        )
        edge_buckets: dict[tuple[str, str], list[int]] = defaultdict(list)
        for edge in filtered_projection.edges:
            source_id = visible_ancestor(selected_scope(edge.source_id))
            target_id = visible_ancestor(selected_scope(edge.target_id))
            if source_id is None or target_id is None or source_id == target_id:
                continue
            edge_buckets[(source_id, target_id)].extend(edge.edge_indices)

        node_depths = {selected: 0} if selected in visible_ids else {}
        edge_depths: dict[tuple[str, str], int] = {}
        incoming_pairs: set[tuple[str, str]] = set()
        if node_depths:
            direction = ("both", "outgoing", "incoming")[self.direction.get_selected()]
            depth_index = self.depth.get_selected()
            max_depth = None if depth_index == 3 else depth_index + 1
            pending = deque([selected])
            while pending:
                current = pending.popleft()
                current_depth = node_depths[current]
                if max_depth is not None and current_depth >= max_depth:
                    continue
                for source_id, target_id in edge_buckets:
                    if direction in {"both", "outgoing"} and source_id == current:
                        edge_depths[(source_id, target_id)] = min(
                            edge_depths.get((source_id, target_id), current_depth + 1),
                            current_depth + 1,
                        )
                        if target_id not in node_depths:
                            node_depths[target_id] = current_depth + 1
                            pending.append(target_id)
                    if direction in {"both", "incoming"} and target_id == current:
                        edge_depths[(source_id, target_id)] = min(
                            edge_depths.get((source_id, target_id), current_depth + 1),
                            current_depth + 1,
                        )
                        incoming_pairs.add((source_id, target_id))
                        if source_id not in node_depths:
                            node_depths[source_id] = current_depth + 1
                            pending.append(source_id)
        else:
            edge_depths = {pair: 1 for pair in edge_buckets}

        selected_incoming = sum(
            len(indices) for (source_id, target_id), indices in edge_buckets.items()
            if target_id == selected
        )
        selected_outgoing = sum(
            len(indices) for (source_id, target_id), indices in edge_buckets.items()
            if source_id == selected
        )

        for directory in projection.nodes:
            if directory.node_id not in visible_ids:
                continue
            x, y = self._directory_positions[directory.node_id]
            related = directory.node_id in node_depths
            incoming_count = (
                selected_incoming if directory.node_id == selected
                else directory.incoming_count
            )
            outgoing_count = (
                selected_outgoing if directory.node_id == selected
                else directory.outgoing_count
            )
            self._add_node(_Node(
                node_id=self._directory_ui(directory.node_id),
                label=directory.display_name + ("/" if directory.node_id != "." else ""),
                detail=(
                    f"{directory.relative_path} · {directory.file_count} files · "
                    f"{incoming_count} in · {outgoing_count} out"
                ),
                kind="internal",
                x=x,
                y=y,
                group_id=directory.node_id,
                members=directory.file_ids,
                is_group=True,
                dimmed=bool(node_depths) and not related,
                selected=directory.node_id == selected,
                is_directory=True,
                file_count=directory.file_count,
            ))

        for (source_id, target_id), indices in sorted(edge_buckets.items()):
            if (source_id, target_id) not in edge_depths:
                continue
            if source_id not in visible_ids or target_id not in visible_ids:
                continue
            bundle_id = f"@directory-edge:{source_id}\0{target_id}"
            self._edges.append(_Edge(
                self._directory_ui(source_id),
                self._directory_ui(target_id),
                "internal",
                tuple(indices),
                bundle_id=bundle_id,
                bundle_summary=True,
                incoming=(source_id, target_id) in incoming_pairs,
                depth=edge_depths[(source_id, target_id)],
            ))

        if selected in projection.node_by_id:
            directory = projection.node_by_id[selected]
            self._selected_sources = set(directory.file_ids)
            self._show_text(
                f"{directory.relative_path}\n{directory.file_count} files · "
                f"{selected_incoming} incoming · {selected_outgoing} outgoing"
            )
            self._show_directory_file_list(selected)
        self.status.set_text(
            f"Only Directories · {len(visible_ids)} directories · "
            f"{sum(len(indices) for pair, indices in edge_buckets.items() if pair in edge_depths)} file relationships"
        )

    def _build_directory_file_explore(self, candidates: tuple[int, ...]) -> None:
        directory_id = self._selected_directory
        directory = self._directory_projection.node_by_id.get(directory_id)
        if directory is None:
            return
        selected_files = set(directory.file_ids)
        self._selected_sources = set(selected_files)
        direction = ("both", "outgoing", "incoming")[self.direction.get_selected()]
        depth_index = self.depth.get_selected()
        depth = None if depth_index == 3 else depth_index + 1
        edge_depths: dict[int, int] = {}
        node_depths: dict[str, int] = {node_id: 0 for node_id in selected_files}
        for node_id in selected_files:
            neighborhood = self._model.neighborhood(node_id, direction, depth, candidates)
            for related, related_depth in neighborhood.node_depths.items():
                node_depths[related] = min(node_depths.get(related, related_depth), related_depth)
            for edge_index, related_depth in neighborhood.edge_depths.items():
                edge_depths[edge_index] = min(
                    edge_depths.get(edge_index, related_depth), related_depth
                )
        active_groups = {self._model.group_for_node(node_id, self._grouping) for node_id in node_depths}
        self._add_group_nodes(dimmed=True, active=active_groups)
        self._selected_sources = set(selected_files)
        incoming_indices = {
            index for node_id in selected_files
            for index in self._model.neighborhood(
                node_id, "incoming", depth, candidates
            ).edge_indices
        }
        outgoing_targets = {
            self._model.graph.edges[index].target
            for node_id in selected_files
            for index in self._model.outgoing.get(node_id, ())
            if index in candidates
        }
        for node_id in node_depths:
            self._add_file_node(
                node_id,
                selected=node_id in selected_files,
                outgoing_target=node_id in outgoing_targets,
            )
        for edge_index, edge_depth in sorted(edge_depths.items()):
            edge = self._model.graph.edges[edge_index]
            self._edges.append(_Edge(
                self._endpoint(edge.source, edge.kind),
                self._endpoint(edge.target, edge.kind),
                edge.kind,
                (edge_index,),
                incoming=edge_index in incoming_indices,
                depth=edge_depth,
            ))
        self._show_text(
            f"{directory.relative_path}\n{directory.file_count} files · "
            f"{len(edge_depths)} visible file relationships"
        )
        self._show_edge_list(tuple(edge_depths), edge_depths)
        self.status.set_text(
            f"Picked directory in All · {len(directory.file_ids)} files · "
            f"{len(edge_depths)} relationships · depth {depth or 'all'}"
        )

    def _show_directory_file_list(self, directory_id: str) -> None:
        self._detail_group_id = None
        self._detail_directory_id = directory_id
        self.detail_search.set_text("")
        self.detail_search.set_visible(True)
        self._populate_directory_files()

    def _populate_directory_files(self) -> None:
        directory_id = self._detail_directory_id
        if directory_id is None:
            return
        self._clear_details_list()
        file_ids = self._directory_projection.node_by_id[directory_id].file_ids
        query = self.detail_search.get_text().strip().casefold()
        matching = [
            node_id for node_id in file_ids
            if query in self._model.node_by_id[node_id].relative_path.casefold()
        ]
        for node_id in matching[:120]:
            node = self._model.node_by_id[node_id]
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            button = Gtk.Button(label=node.relative_path)
            button.set_hexpand(True)
            button.add_css_class("theme-toolbar-button")
            button.connect("clicked", self._on_detail_file, node_id)
            row.append(button)
            self._append_open_file_action(node_id, row)
            self.details_list.append(row)
        if len(matching) > 120:
            self.details_list.append(
                Gtk.Label(label=f"Showing 120 of {len(matching)} files; refine the search.")
            )

    @staticmethod
    def _directory_ui(directory_id: str) -> str:
        return f"@directory:{directory_id}"

    def _build_overview(self, candidates: tuple[int, ...]) -> None:
        self._add_group_nodes()
        bundles = self._model.bundle_edges(self._grouping, candidates)
        if len(bundles) > self._MAX_OVERVIEW_BUNDLES:
            shown = sorted(
                bundles,
                key=lambda bundle: (-len(bundle.edge_indices), bundle.source_group, bundle.target_group),
            )[:self._MAX_OVERVIEW_BUNDLES]
            self._edges.extend(self._bundle_edge(bundle) for bundle in shown)
            self.status.set_text(
                f"Overview · showing {len(shown)} of {len(bundles)} grouped connections; Full map shows all"
            )
            return
        self._edges.extend(self._bundle_edge(bundle) for bundle in bundles)
        self.status.set_text("Overview · grouped architecture")

    def _build_full(self, candidates: tuple[int, ...]) -> None:
        self._add_group_nodes()
        for bundle in self._model.bundle_edges(self._grouping, candidates):
            if bundle.bundle_id in self._expanded_bundles or (
                bundle.bundle_id not in self._collapsed_bundles
                and self._zoom >= 1.25 and len(bundle.edge_indices) <= 5
            ):
                self._expand_bundle(bundle)
            else:
                self._edges.append(self._bundle_edge(bundle))
        count = sum(len(edge.indices) for edge in self._edges)
        self.status.set_text(f"Full map · {len(self._edges)} bundles · {count} relationships")
        if count > 500:
            self.status.set_text(f"Dense map · {len(self._edges)} bundles / {count} relationships; expand bundles individually")

    def _build_explore(self, candidates: tuple[int, ...]) -> None:
        model = self._model
        selected = self._selected_node
        direction = ("both", "outgoing", "incoming")[self.direction.get_selected()]
        depth_index = self.depth.get_selected()
        depth = None if depth_index == 3 else depth_index + 1
        neighborhood = model.neighborhood(selected, direction, depth, candidates)
        incoming = model.neighborhood(selected, "incoming", depth, candidates)
        self._selected_sources = {selected}
        direct_outgoing = {
            model.graph.edges[index].target
            for index in model.outgoing.get(selected, ())
            if index in candidates
        }
        connected = set(neighborhood.node_depths)
        active_groups = {model.group_for_node(node, self._grouping) for node in connected}
        self._add_group_nodes(dimmed=True, active=active_groups)
        for node_id, distance in neighborhood.node_depths.items():
            self._add_file_node(
                node_id,
                selected=(node_id == selected),
                dimmed=False,
                outgoing_target=node_id in direct_outgoing,
            )
        for index in neighborhood.edge_indices:
            edge = model.graph.edges[index]
            source = self._endpoint(edge.source, edge.kind)
            target = self._endpoint(edge.target, edge.kind)
            self._edges.append(_Edge(
                source, target, edge.kind, (index,),
                incoming=index in incoming.edge_indices,
                depth=neighborhood.edge_depths[index],
            ))
        self._show_node_details(selected)
        self._show_edge_list(neighborhood.edge_indices, neighborhood.edge_depths)
        self._append_open_file_action(selected)
        self.status.set_text(f"Explore · {len(connected) - 1} related files · depth {depth or 'all'}")

    def _add_group_nodes(self, dimmed: bool = False, active: set[str] | None = None) -> None:
        for group_id in sorted(self._group_ids):
            x, y = self._group_positions[group_id]
            summary = self._groups.get(group_id)
            kind = group_id.partition(":")[0] if ":" in group_id else "internal"
            if kind not in {"internal", "external", "stdlib", "unresolved"}:
                kind = "internal"
            if summary is None:
                count = self._external_group_counts.get(group_id, 0)
                label = group_id.partition(":")[2].strip()
                detail = f"{kind.upper()} · {count} incoming"
                members = ()
            else:
                label = summary.label
                detail = f"{len(summary.node_ids)} files · {summary.incoming_count} in · {summary.outgoing_count} out"
                members = summary.node_ids
            self._add_node(_Node(
                self._group_ui(group_id), label, detail, kind, x, y,
                group_id=group_id, members=members, is_group=True,
                dimmed=dimmed and active is not None and group_id not in active,
            ))
            if group_id in self._expanded_groups and summary is not None and not dimmed:
                for node_id in summary.node_ids:
                    self._add_file_node(node_id)

    def _add_file_node(
        self,
        node_id: str,
        selected: bool = False,
        dimmed: bool = False,
        outgoing_target: bool = False,
    ) -> None:
        if node_id in self._node_by_id:
            node = self._node_by_id[node_id]
            node.selected = node.selected or selected
            node.dimmed = node.dimmed and dimmed
            node.outgoing_target = node.outgoing_target or outgoing_target
            return
        source = self._model.node_by_id[node_id]
        x, y = self._file_positions[node_id]
        counts = self._model.node_counts(node_id)
        detail = f"{counts['outgoing_dependencies']} out · {counts['incoming_dependencies']} in"
        self._add_node(_Node(
            node_id, source.display_name, detail, "internal", x, y,
            file_path=source.file_path,
            group_id=self._model.group_for_node(node_id, self._grouping),
            selected=selected, dimmed=dimmed,
            outgoing_target=outgoing_target,
        ))

    def _expand_bundle(self, bundle: DependencyBundle) -> None:
        endpoints = set()
        for index in bundle.edge_indices:
            edge = self._model.graph.edges[index]
            endpoints.update(endpoint for endpoint in (edge.source, edge.target) if endpoint in self._model.node_by_id)
        for node_id in sorted(endpoints):
            self._add_file_node(node_id)
        for index in bundle.edge_indices:
            edge = self._model.graph.edges[index]
            source = self._endpoint(edge.source, edge.kind)
            target = self._endpoint(edge.target, edge.kind)
            self._edges.append(_Edge(
                source, target, edge.kind, (index,), bundle_id=bundle.bundle_id
            ))

    def _endpoint(self, node_id: str, kind: str) -> str:
        if node_id in self._model.node_by_id:
            self._add_file_node(node_id)
            return node_id
        group_id = self._model.group_for_node(node_id, self._grouping, kind)
        visual_id = self._group_ui(group_id)
        if visual_id not in self._node_by_id:
            x = max((position[0] for position in self._group_positions.values()), default=48) + 350
            y = 40 + len(self._node_by_id) * 16
            self._add_node(_Node(visual_id, node_id, kind.upper(), kind, x, y, group_id=group_id, is_group=True))
        return visual_id

    def _add_node(self, node: _Node) -> None:
        self._node_by_id[node.node_id] = node
        self._nodes.append(node)

    def _bundle_edge(self, bundle: DependencyBundle) -> _Edge:
        return _Edge(
            self._group_ui(bundle.source_group),
            self._group_ui(bundle.target_group),
            bundle.kind,
            bundle.edge_indices,
            bundle_id=bundle.bundle_id,
            bundle_summary=True,
        )

    @staticmethod
    def _group_ui(group_id: str) -> str:
        return f"@group:{group_id}"

    def _cache_geometry(self) -> None:
        self._routes = []
        self._node_grid.clear()
        self._edge_grid.clear()
        selected_targets = sorted({
            edge.target for edge in self._edges
            if self._mode == "explore" and edge.source in self._selected_sources
            and edge.target in self._node_by_id
        }, key=lambda node_id: (
            self._node_by_id[node_id].y,
            self._node_by_id[node_id].x,
            node_id,
        ))
        source_offsets = {
            node_id: (index - (len(selected_targets) - 1) / 2) * min(
                14.0, 42.0 / max(1, len(selected_targets) - 1)
            )
            for index, node_id in enumerate(selected_targets)
        }
        for index, edge in enumerate(self._edges):
            source = self._node_by_id.get(edge.source)
            target = self._node_by_id.get(edge.target)
            if source is None or target is None:
                self._routes.append(())
                continue
            route = self._route(
                source,
                target,
                source_offset=(
                    source_offsets.get(edge.target, 0.0)
                    if edge.source in self._selected_sources else 0.0
                ),
            )
            self._routes.append(route)
            self._index_bounds(self._edge_grid, index, route)
        for index, node in enumerate(self._nodes):
            bounds = (
                (node.x, node.y), (node.x + self.NODE_WIDTH, node.y),
                (node.x, node.y + self.NODE_HEIGHT),
                (node.x + self.NODE_WIDTH, node.y + self.NODE_HEIGHT),
            )
            self._index_bounds(self._node_grid, index, bounds)

    def _route(
        self,
        source: _Node,
        target: _Node,
        source_offset: float = 0.0,
    ) -> tuple[tuple[float, float], ...]:
        sy = source.y + self.NODE_HEIGHT / 2 + source_offset
        ty = target.y + self.NODE_HEIGHT / 2
        if source.node_id == target.node_id:
            start = (source.x + self.NODE_WIDTH, source.y + 24.0)
            end = (source.x + self.NODE_WIDTH, source.y + 56.0)
            c1 = (source.x + self.NODE_WIDTH + 64.0, source.y - 4.0)
            c2 = (source.x + self.NODE_WIDTH + 64.0, source.y + self.NODE_HEIGHT + 8.0)
        elif abs(target.x - source.x) < self.NODE_WIDTH:
            start = (source.x + self.NODE_WIDTH, sy)
            end = (target.x + self.NODE_WIDTH, ty)
            channel = max(start[0], end[0]) + 64.0
            c1, c2 = (channel, sy), (channel, ty)
        elif target.x >= source.x + self.NODE_WIDTH:
            start, end = (source.x + self.NODE_WIDTH, sy), (target.x, ty)
            direction = 1
            bend = max(40, abs(end[0] - start[0]) * 0.42)
            c1, c2 = (start[0] + bend * direction, start[1]), (end[0] - bend * direction, end[1])
        elif target.x + self.NODE_WIDTH <= source.x:
            start, end = (source.x, sy), (target.x + self.NODE_WIDTH, ty)
            direction = -1
            bend = max(40, abs(end[0] - start[0]) * 0.42)
            c1, c2 = (start[0] + bend * direction, start[1]), (end[0] - bend * direction, end[1])
        else:
            start, end = (source.x + self.NODE_WIDTH / 2, source.y + self.NODE_HEIGHT), (target.x + self.NODE_WIDTH / 2, target.y)
            direction = 1 if end[0] >= start[0] else -1
            bend = max(40, abs(end[0] - start[0]) * 0.42)
            c1, c2 = (start[0] + bend * direction, start[1]), (end[0] - bend * direction, end[1])
        points = []
        for step in range(17):
            t = step / 16
            u = 1 - t
            points.append((
                u**3 * start[0] + 3 * u**2 * t * c1[0] + 3 * u * t**2 * c2[0] + t**3 * end[0],
                u**3 * start[1] + 3 * u**2 * t * c1[1] + 3 * u * t**2 * c2[1] + t**3 * end[1],
            ))
        return tuple(points)

    @staticmethod
    def _index_bounds(grid: dict[tuple[int, int], list[int]], index: int, points: tuple[tuple[float, float], ...]) -> None:
        if not points:
            return
        cell = 320.0
        xs, ys = [point[0] for point in points], [point[1] for point in points]
        for x in range(math.floor(min(xs) / cell), math.floor(max(xs) / cell) + 1):
            for y in range(math.floor(min(ys) / cell), math.floor(max(ys) / cell) + 1):
                grid[(x, y)].append(index)

    def _draw(self, _area: Gtk.DrawingArea, context: object, width: int, height: int, *_args: object) -> None:
        if not self._nodes:
            return
        origin = self._origin()
        context.save()
        context.translate(*self._pan)
        context.translate(*origin)
        context.scale(self._zoom, self._zoom)
        viewport = (
            (-self._pan[0] - origin[0]) / self._zoom,
            (-self._pan[1] - origin[1]) / self._zoom,
            (width - self._pan[0] - origin[0]) / self._zoom,
            (height - self._pan[1] - origin[1]) / self._zoom,
        )
        visible_edges = self._visible_indices(self._edge_grid, viewport)
        visible_edges = tuple(sorted(
            visible_edges,
            key=lambda index: self._edges[index].source in self._selected_sources
            or (
                self._view_kind == "directories"
                and self._edges[index].source == self._directory_ui(self._selected_directory)
            ),
        ))
        for index in visible_edges:
            edge = self._edges[index]
            route = self._routes[index]
            if not route:
                continue
            color = self._edge_color(edge)
            focused = bool(self._focus_edges.intersection(edge.indices))
            selected_outgoing = (
                self._mode == "explore"
                and (
                    edge.source in self._selected_sources
                    or (
                        self._view_kind == "directories"
                        and edge.source == self._directory_ui(self._selected_directory)
                    )
                )
                and not edge.bundle_summary
            )
            is_directory_edge = self._view_kind == "directories" and edge.source.startswith("@directory:")
            if selected_outgoing:
                context.set_source_rgba(0.025, 0.045, 0.065, 0.98)
                context.set_line_width(7.0)
                context.move_to(*route[0])
                for point in route[1:]:
                    context.line_to(*point)
                context.stroke()
            if is_directory_edge:
                context.set_source_rgba(0.02, 0.08, 0.10, 0.96)
                context.set_line_width(6.5)
                context.move_to(*route[0])
                for point in route[1:]:
                    context.line_to(*point)
                context.stroke()
            context.set_source_rgba(*color, 1.0 if focused or index == self._hover_edge else 0.78)
            context.set_line_width(
                4.8 if is_directory_edge else (
                    4.0 if selected_outgoing else (
                        3.2 if focused or index == self._hover_edge
                        else (3.0 if edge.bundle_summary else 1.8)
                    )
                )
            )
            context.move_to(*route[0])
            for point in route[1:]:
                context.line_to(*point)
            context.stroke()
            self._arrow(context, route[-2], route[-1], color)
            if edge.bundle_summary and len(edge.indices) > 1:
                context.set_font_size(10)
                context.set_source_rgba(*color, 1)
                middle = route[len(route) // 2]
                context.move_to(middle[0] + 5, middle[1] - 4)
                context.show_text(str(len(edge.indices)))

        foreground = self.canvas.get_style_context().get_color()
        for index in self._visible_indices(self._node_grid, viewport):
            node = self._nodes[index]
            selected = (
                self._all_nodes_selected
                or node.selected
                or node.outgoing_target
                or node.node_id in getattr(self, "_multi_select_node_ids", set())
                or node.node_id
                == getattr(self, "_multi_select_hover_node_id", None)
            )
            color = (
                (0.97, 0.99, 1.0) if node.selected or node.outgoing_target
                else self._kind_color(node.kind)
            )
            if (
                self._all_nodes_selected
                or node.node_id in getattr(self, "_multi_select_node_ids", set())
                or node.node_id
                == getattr(self, "_multi_select_hover_node_id", None)
            ):
                color = (0.97, 0.99, 1.0)
            alpha = 0.12 if node.dimmed else (0.28 if selected else 0.18)
            context.set_source_rgba(*color, alpha)
            context.rectangle(node.x, node.y, self.NODE_WIDTH, self.NODE_HEIGHT)
            context.fill_preserve()
            context.set_source_rgba(*color, 0.32 if node.dimmed else 0.95)
            context.set_line_width(
                2.8 if selected else (2.2 if node.outgoing_target else 1.6)
            )
            context.stroke()
            text_alpha = 0.35 if node.dimmed else 1.0
            context.set_source_rgba(foreground.red, foreground.green, foreground.blue, foreground.alpha * text_alpha)
            context.set_font_size(12 if node.is_group else 13)
            context.move_to(node.x + 12, node.y + 27)
            context.show_text(self._fit(node.label, 27))
            context.set_font_size(10)
            context.move_to(node.x + 12, node.y + 51)
            context.show_text(self._fit(node.detail, 35))
        context.restore()

    @staticmethod
    def _visible_indices(
        grid: dict[tuple[int, int], list[int]],
        viewport: tuple[float, float, float, float],
    ) -> tuple[int, ...]:
        cell_size = 320.0
        left, top, right, bottom = viewport
        visible: set[int] = set()
        for x in range(math.floor(left / cell_size), math.floor(right / cell_size) + 1):
            for y in range(math.floor(top / cell_size), math.floor(bottom / cell_size) + 1):
                visible.update(grid.get((x, y), ()))
        return tuple(sorted(visible))

    def _origin(self) -> tuple[float, float]:
        if not self._nodes:
            return 0.0, 0.0
        max_x = max(node.x + self.NODE_WIDTH for node in self._nodes)
        max_y = max(node.y + self.NODE_HEIGHT for node in self._nodes)
        width = self.canvas.get_content_width() or self.canvas.get_width()
        height = self.canvas.get_content_height() or self.canvas.get_height()
        return max(24, (width - max_x * self._zoom) / 2), max(24, (height - max_y * self._zoom) / 2)

    @staticmethod
    def _arrow(context: object, start: tuple[float, float], end: tuple[float, float], color: tuple[float, float, float]) -> None:
        angle = math.atan2(end[1] - start[1], end[0] - start[0])
        bx, by = end[0] - 9 * math.cos(angle), end[1] - 9 * math.sin(angle)
        context.set_source_rgba(*color, 0.95)
        context.move_to(*end)
        context.line_to(bx + 4 * math.sin(angle), by - 4 * math.cos(angle))
        context.line_to(bx - 4 * math.sin(angle), by + 4 * math.cos(angle))
        context.close_path()
        context.fill()

    def _on_click(self, _gesture: Gtk.GestureClick, _count: int, x: float, y: float) -> None:
        self._all_nodes_selected = False
        gx, gy = self._graph_point(x, y)
        cell = (math.floor(gx / 320), math.floor(gy / 320))
        for index in reversed(self._node_grid.get(cell, ())):
            node = self._nodes[index]
            if node.x <= gx <= node.x + self.NODE_WIDTH and node.y <= gy <= node.y + self.NODE_HEIGHT:
                if node.is_directory and node.group_id is not None:
                    children = [
                        child.node_id for child in self._directory_projection.nodes
                        if child.parent_id == node.group_id
                    ]
                    if children:
                        if node.group_id in self._collapsed_directories:
                            self._collapsed_directories.remove(node.group_id)
                        else:
                            self._collapsed_directories.add(node.group_id)
                    self._on_pick_selected(None, "directory", node.group_id)
                    return
                if node.is_group:
                    if node.members:
                        if node.group_id in self._expanded_groups:
                            self._expanded_groups.remove(node.group_id)
                        else:
                            self._expanded_groups.add(node.group_id)
                        self._show_group_details(node.group_id)
                        self._render()
                    else:
                        self._show_text(f"{node.label}\n{node.kind} dependency group")
                    return
                self._selected_node = node.node_id
                if self._mode != "explore":
                    self._mode = "explore"
                    self.mode_select.set_selected(1)
                else:
                    self._render()
                return
        edge_index = self._hit_edge(gx, gy)
        if edge_index is None:
            return
        edge = self._edges[edge_index]
        if edge.bundle_summary:
            self._expanded_bundles.add(edge.bundle_id)
            self._collapsed_bundles.discard(edge.bundle_id)
            self._show_bundle_details(edge)
            self._render()
        elif edge.bundle_id:
            if edge.bundle_id in self._expanded_bundles:
                self._expanded_bundles.remove(edge.bundle_id)
            self._collapsed_bundles.add(edge.bundle_id)
            self._show_edge_details(edge.indices[0], edge.depth)
            self._render()
        else:
            self._show_edge_details(edge.indices[0], edge.depth)

    def _on_motion(self, _controller: Gtk.EventControllerMotion, x: float, y: float) -> None:
        gx, gy = self._graph_point(x, y)
        edge_index = self._hit_edge(gx, gy, 12)
        if edge_index == self._hover_edge:
            return
        self._hover_edge = edge_index
        if edge_index is None:
            self.canvas.set_tooltip_text(None)
        else:
            edge = self._edges[edge_index]
            if edge.bundle_summary:
                self.canvas.set_tooltip_text(
                    f"{len(edge.indices)} relationships · "
                    f"{self._node_by_id[edge.source].label} -> "
                    f"{self._node_by_id[edge.target].label} · click to expand"
                )
            else:
                text = self._edge_description(edge.indices[0])
                if edge.depth > 1:
                    text += f" · traversal depth {edge.depth}"
                self.canvas.set_tooltip_text(text)
        self.canvas.queue_draw()

    def _graph_point(self, x: float, y: float) -> tuple[float, float]:
        ox, oy = self._origin()
        return (x - self._pan[0] - ox) / self._zoom, (y - self._pan[1] - oy) / self._zoom

    def node_at(self, x: float, y: float) -> _Node | None:
        gx, gy = self._graph_point(x, y)
        cell = (math.floor(gx / 320), math.floor(gy / 320))
        for index in reversed(self._node_grid.get(cell, ())):
            node = self._nodes[index]
            if (
                node.x <= gx <= node.x + self.NODE_WIDTH
                and node.y <= gy <= node.y + self.NODE_HEIGHT
            ):
                return node
        return None

    def select_all_nodes(self) -> None:
        self._all_nodes_selected = bool(self._nodes)
        self.canvas.queue_draw()

    def _hit_edge(self, x: float, y: float, tolerance: float = 9) -> int | None:
        cell = (math.floor(x / 320), math.floor(y / 320))
        best, distance = None, tolerance
        for index in self._edge_grid.get(cell, ()):
            route = self._routes[index]
            current = min((math.hypot(x - px, y - py) for px, py in route), default=math.inf)
            if current < distance:
                best, distance = index, current
        return best

    def _show_group_details(self, group_id: str) -> None:
        summary = self._groups[group_id]
        self._show_text(
            f"{group_id}\n{len(summary.node_ids)} files · {summary.outgoing_count} outgoing · "
            f"{summary.incoming_count} incoming · {summary.external_count} external"
        )
        self._detail_group_id = group_id
        self._detail_directory_id = None
        self.detail_search.set_text("")
        self.detail_search.set_visible(True)
        self._populate_group_files()

    def _populate_group_files(self) -> None:
        group_id = self._detail_group_id
        if group_id is None:
            return
        summary = self._groups[group_id]
        self._clear_details_list()
        query = self.detail_search.get_text().strip().casefold()
        matching = [
            node_id for node_id in summary.node_ids
            if query in self._model.node_by_id[node_id].relative_path.casefold()
        ]
        for node_id in matching[:120]:
            node = self._model.node_by_id[node_id]
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            button = Gtk.Button(label=node.relative_path)
            button.set_hexpand(True)
            button.add_css_class("theme-toolbar-button")
            button.connect("clicked", self._on_detail_file, node_id)
            row.append(button)
            self._append_open_file_action(node_id, row)
            self.details_list.append(row)
        if len(matching) > 120:
            self.details_list.append(Gtk.Label(label=f"Showing 120 of {len(matching)} files; refine the filter."))

    def _on_group_file_search(self, _entry: Gtk.SearchEntry) -> None:
        if self._detail_group_id is not None:
            self._populate_group_files()
        elif getattr(self, "_detail_directory_id", None) is not None:
            self._populate_directory_files()

    def _show_node_details(self, node_id: str) -> None:
        self._detail_group_id = None
        self._detail_directory_id = None
        self.detail_search.set_visible(False)
        node = self._model.node_by_id[node_id]
        counts = self._model.node_counts(node_id)
        self._show_text(
            f"{node.relative_path}\n{counts['direct_dependencies']} direct · "
            f"{counts['incoming_dependencies']} incoming · {counts['outgoing_dependencies']} outgoing · "
            f"{counts['transitive_dependencies']} transitive · {counts['external_dependencies']} external · "
            f"{'in a cycle' if counts['circular'] else 'not in a detected cycle'}"
        )

    def _show_edge_list(
        self, indices: tuple[int, ...], edge_depths: dict[int, int] | None = None
    ) -> None:
        self._clear_details_list()
        for index in indices[:80]:
            path_depth = edge_depths.get(index, 1) if edge_depths is not None else 1
            label = self._edge_description(index)
            if path_depth > 1:
                label += f" · path depth {path_depth} (direct edge)"
            button = Gtk.Button(label=label)
            button.add_css_class("theme-toolbar-button")
            button.connect("clicked", self._on_edge_detail, index, path_depth)
            self.details_list.append(button)

    def _show_bundle_details(self, edge: _Edge) -> None:
        source = self._node_by_id[edge.source].label
        target = self._node_by_id[edge.target].label
        self._show_text(f"Bundle · {len(edge.indices)} relationships\n{source} -> {target}\nClick again to collapse")
        self._show_edge_list(edge.indices)

    def _show_edge_details(self, index: int, path_depth: int | None = None) -> None:
        self._detail_group_id = None
        self._detail_directory_id = None
        self.detail_search.set_visible(False)
        description = self._edge_description(index)
        if path_depth is not None and path_depth > 1:
            description += f"\nDirect edge found at traversal depth {path_depth}."
        self._show_text(description)
        self._show_edge_list((index,))
        self._append_open_file_action(self._model.graph.edges[index].source)

    def _append_open_file_action(self, node_id: str, parent: Gtk.Box | None = None) -> None:
        if self._on_file_navigate is None:
            return
        node = self._model.node_by_id.get(node_id)
        if node is None:
            return
        button = Gtk.Button.new_from_icon_name("document-open-symbolic")
        button.add_css_class("theme-toolbar-button")
        button.set_tooltip_text(f"Open {node.relative_path}")
        button.connect("clicked", self._on_open_file, node.file_path)
        (parent or self.details_list).append(button)

    def _on_open_file(self, _button: Gtk.Button, file_path: Path) -> None:
        if self._on_file_navigate is not None:
            self._on_file_navigate(file_path)

    def _edge_description(self, index: int) -> str:
        edge = self._model.graph.edges[index]
        source = self._model.node_by_id.get(edge.source)
        target = self._model.node_by_id.get(edge.target)
        source_name = source.relative_path if source else edge.source
        target_name = target.relative_path if target else edge.target
        return f"{source_name} -> {target_name} · {edge.kind} · {edge.import_name} · line {edge.line} · direct"

    def _show_text(self, text: str) -> None:
        self.details.set_text(text)

    def _clear_details_list(self) -> None:
        for child in list(self.details_list):
            self.details_list.remove(child)

    def _on_detail_file(self, _button: Gtk.Button, node_id: str) -> None:
        self._on_pick_selected(_button, "file", node_id)

    def _on_edge_detail(self, _button: Gtk.Button, index: int, path_depth: int = 1) -> None:
        self._show_edge_details(index, path_depth)

    def _on_search(self, entry: Gtk.SearchEntry) -> None:
        if self._model is None:
            return
        matches = self._model.relationship(entry.get_text())
        if not matches:
            self._show_text(f"No matching relationship: {entry.get_text()}")
            self.status.set_text("No matching relationship")
            return
        index = matches[0]
        edge = self._model.graph.edges[index]
        if self._view_kind == "directories":
            self._view_kind = "all"
            self._updating_controls = True
            self.view_select.set_selected(0)
            self._updating_controls = False
        self._updating_controls = True
        self.direction.set_selected(0)
        self.kind.set_selected(0)
        self.file_type.set_selected(0)
        self.cycles.set_active(False)
        self._updating_controls = False
        if edge.source in self._model.node_by_id:
            self._selected_node = edge.source
            self._mode = "explore"
            self.mode_select.set_selected(1)
        self._focus_edges = set(matches)
        self._render()
        self._show_edge_details(index)
        self._center_nodes((edge.source, edge.target))

    def _center_nodes(self, node_ids: tuple[str, ...]) -> None:
        nodes = [self._node_by_id[node_id] for node_id in node_ids if node_id in self._node_by_id]
        if not nodes:
            return
        ox, oy = self._origin()
        center_x = (min(node.x for node in nodes) + max(node.x + self.NODE_WIDTH for node in nodes)) / 2
        center_y = (min(node.y for node in nodes) + max(node.y + self.NODE_HEIGHT for node in nodes)) / 2
        self._pan = (
            self.scroller.get_width() / 2 - (center_x * self._zoom + ox),
            self.scroller.get_height() / 2 - (center_y * self._zoom + oy),
        )
        self.canvas.queue_draw()

    def _on_view_changed(self, dropdown: Gtk.DropDown, _pspec: object) -> None:
        if self._updating_controls:
            return
        self._view_kind = "all" if dropdown.get_selected() == 0 else "directories"
        self.group_select.set_sensitive(self._view_kind == "all")
        if self._picked_item is not None:
            item_kind, item_id = self._picked_item
            if item_kind == "file":
                self._selected_directory = self._model.group_for_node(item_id, "directory")
            else:
                self._selected_directory = item_id
        self._render()
        if self._selected_directory is not None and self._view_kind == "directories":
            self._center_nodes((self._directory_ui(self._selected_directory),))

    def _on_pick_search_changed(self, _entry: Gtk.SearchEntry) -> None:
        self._populate_pick_results()

    def _populate_pick_results(self) -> None:
        for child in list(self.pick_results):
            self.pick_results.remove(child)
        if self._directory_projection is None or self._model is None:
            return
        query = self.pick_search.get_text().strip().casefold()
        directories = [
            node for node in self._directory_projection.nodes
            if query in node.relative_path.casefold()
            or query in node.display_name.casefold()
        ]
        files = [
            node for node in self._model.graph.nodes
            if query in node.relative_path.casefold()
            or query in node.display_name.casefold()
        ]
        for title, items, item_kind in (
            ("Directories", directories, "directory"),
            ("Files", files, "file"),
        ):
            if not items:
                continue
            heading = Gtk.Label(label=title)
            heading.set_halign(Gtk.Align.START)
            heading.add_css_class("complexity-panel-title")
            self.pick_results.append(heading)
            for item in items[:150]:
                row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                icon_name = "folder-symbolic" if item_kind == "directory" else "text-x-generic-symbolic"
                icon = Gtk.Image.new_from_icon_name(icon_name)
                icon.set_pixel_size(16)
                button = Gtk.Button()
                button.set_hexpand(True)
                button.set_halign(Gtk.Align.FILL)
                button.add_css_class("theme-toolbar-button")
                label = item.relative_path
                if item_kind == "directory" and label != ".":
                    label += "/"
                button.set_child(Gtk.Label(label=label, xalign=0))
                button.connect("clicked", self._on_pick_selected, item_kind, item.node_id)
                row.append(icon)
                row.append(button)
                self.pick_results.append(row)
            if len(items) > 150:
                self.pick_results.append(
                    Gtk.Label(label=f"Showing 150 of {len(items)}; refine the search.")
                )
        if not directories and not files:
            self.pick_results.append(Gtk.Label(label="No matching files or directories."))

    def _on_pick_selected(
        self, _button: Gtk.Button, item_kind: str, item_id: str
    ) -> None:
        if self._model is None:
            return
        if self._pre_pick_mode is None:
            self._pre_pick_mode = (self._mode, self._selected_node)
            self._pre_pick_view = self._view_kind
        if item_kind == "file" and self._view_kind == "directories":
            self._view_kind = "all"
            self._updating_controls = True
            self.view_select.set_selected(0)
            self._updating_controls = False
        self._picked_item = (item_kind, item_id)
        self.picked_label.set_text(item_id)
        self.clear_pick_button.set_sensitive(True)
        self._selected_node = item_id if item_kind == "file" else None
        self._selected_directory = (
            self._model.group_for_node(item_id, "directory")
            if item_kind == "file" else item_id
        )
        self._mode = "explore"
        self._updating_controls = True
        self.mode_select.set_selected(1)
        self._updating_controls = False
        self.pick_menu.popdown()
        self._render()
        if item_kind == "file":
            self._center_nodes((item_id,))
        elif self._view_kind == "directories":
            self._center_nodes((self._directory_ui(item_id),))
        elif self._directory_projection.node_by_id[item_id].file_ids:
            self._center_nodes(self._directory_projection.node_by_id[item_id].file_ids[:3])

    def _on_clear_pick(self, _button: Gtk.Button) -> None:
        if self._picked_item is None:
            return
        previous_mode, previous_node = self._pre_pick_mode or ("overview", None)
        previous_view = self._pre_pick_view or self._view_kind
        self._picked_item = None
        self._pre_pick_mode = None
        self._pre_pick_view = None
        self._selected_node = previous_node
        self._selected_directory = None
        self._focus_edges.clear()
        self.picked_label.set_text("No selection")
        self.clear_pick_button.set_sensitive(False)
        self._mode = previous_mode
        self._updating_controls = True
        self.mode_select.set_selected(("overview", "explore", "full").index(previous_mode))
        self._view_kind = previous_view
        self.view_select.set_selected(0 if previous_view == "all" else 1)
        self._updating_controls = False
        self._render()

    @staticmethod
    def _directory_ui(directory_id: str) -> str:
        return f"@directory:{directory_id}"

    def _on_mode_changed(self, dropdown: Gtk.DropDown, _pspec: object) -> None:
        if self._updating_controls:
            return
        self._mode = ("overview", "explore", "full")[dropdown.get_selected()]
        if self._mode != "explore":
            self._picked_item = None
            self._pre_pick_mode = None
            self._pre_pick_view = None
            self._selected_directory = None
            self.picked_label.set_text("No selection")
            self.clear_pick_button.set_sensitive(False)
            self._selected_node = None
            self._focus_edges.clear()
        self._render()

    def _on_group_changed(self, dropdown: Gtk.DropDown, _pspec: object) -> None:
        if self._updating_controls:
            return
        self._grouping = ("directory", "module", "file-type", "cluster")[dropdown.get_selected()]
        if self._model is not None:
            self._expanded_groups.clear()
            self._expanded_bundles.clear()
            self._prepare_layout()
            self._render()

    def _on_filters_changed(self, *_args: object) -> None:
        if self._model is not None and not self._updating_controls:
            self._render()

    def _on_reset(self, _button: Gtk.Button) -> None:
        self._updating_controls = True
        for control in (self.mode_select, self.group_select, self.direction, self.kind, self.file_type, self.depth):
            control.set_selected(0)
        self.cycles.set_active(False)
        self.search.set_text("")
        self._updating_controls = False
        self._mode = "overview"
        self._grouping = "directory"
        self._selected_node = None
        self._selected_sources.clear()
        self._picked_item = None
        self._pre_pick_mode = None
        self._pre_pick_view = None
        self._selected_directory = None
        self.picked_label.set_text("No selection")
        self.clear_pick_button.set_sensitive(False)
        self._expanded_groups.clear()
        self._expanded_bundles.clear()
        self._focus_edges.clear()
        if self._model is not None:
            self._prepare_layout()
            self._render()

    def _on_pan_begin(self, _gesture: Gtk.GestureDrag, _x: float, _y: float) -> None:
        self._drag_origin = self._pan

    def _on_pan_update(self, _gesture: Gtk.GestureDrag, dx: float, dy: float) -> None:
        self._pan = (self._drag_origin[0] + dx, self._drag_origin[1] + dy)
        self.canvas.queue_draw()

    def zoom_in(self) -> None:
        self._zoom = min(2.5, self._zoom * 1.2)
        self._render() if self._mode == "full" else self._render_canvas()

    def zoom_out(self) -> None:
        self._zoom = max(0.45, self._zoom / 1.2)
        self._render() if self._mode == "full" else self._render_canvas()

    def _render_canvas(self) -> None:
        if not self._nodes:
            return
        self.canvas.set_content_width(max(320, math.ceil((max(n.x for n in self._nodes) + self.NODE_WIDTH + 80) * self._zoom)))
        self.canvas.set_content_height(max(280, math.ceil((max(n.y for n in self._nodes) + self.NODE_HEIGHT + 80) * self._zoom)))
        self.canvas.queue_draw()

    def _refresh_metrics(self) -> None:
        for child in list(self.metrics):
            self.metrics.remove(child)
        if self._analysis is None:
            return
        for label, key in (("Files", "total_files"), ("Edges", "total_edges"), ("Internal", "internal_edges"), ("Cycles", "cycle_count")):
            item = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            item.add_css_class("complexity-summary-card")
            name = Gtk.Label(label=label)
            name.add_css_class("complexity-meta-label")
            value = Gtk.Label(label=str(self._analysis.summary[key]))
            value.add_css_class("complexity-summary-value")
            item.append(name)
            item.append(value)
            self.metrics.append(item)

    def _edge_color(self, edge: _Edge) -> tuple[float, float, float]:
        if self._view_kind == "directories" and edge.source.startswith("@directory:"):
            return (0.38, 0.90, 0.98)
        if self._mode == "explore":
            if (
                edge.source in self._selected_sources
                or (
                    self._view_kind == "directories"
                    and edge.source == self._directory_ui(self._selected_directory)
                )
            ) and not edge.bundle_summary:
                return (0.98, 0.99, 1.0)
            if edge.incoming:
                return (0.82, 0.34, 0.72)
            return (0.08, 0.58, 0.72)
        if self._cycle_indices.intersection(edge.indices):
            return (0.92, 0.30, 0.34)
        if edge.kind == "internal":
            return (0.12, 0.66, 0.49)
        return self._kind_color(edge.kind)

    @staticmethod
    def _kind_color(kind: str) -> tuple[float, float, float]:
        return {"internal": (0.12, 0.66, 0.49), "stdlib": (0.20, 0.55, 0.86), "external": (0.89, 0.57, 0.20), "unresolved": (0.86, 0.30, 0.32)}.get(kind, (0.48, 0.55, 0.62))

    @staticmethod
    def _fit(text: str, length: int) -> str:
        return text if len(text) <= length else text[:length - 3] + "..."


__all__ = ["DependencyView"]
