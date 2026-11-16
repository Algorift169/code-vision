from pathlib import Path

from codevision.dependencies import (
    DependencyAnalyzer,
    DependencyEdge,
    DependencyGraph,
    DependencyNode,
    DependencyDirectoryProjection,
    DependencyExplorerModel,
)
from codevision.ui.graphs import DependencyView


def test_project_dependency_graph_detects_internal_edges_and_cycles(tmp_path: Path) -> None:
    package_dir = tmp_path / "pkg"
    package_dir.mkdir()

    (package_dir / "__init__.py").write_text("from .a import value\n", encoding="utf-8")
    (package_dir / "a.py").write_text(
        "from pkg.b import value\nfrom collections import defaultdict\n\nvalue = 1\n",
        encoding="utf-8",
    )
    (package_dir / "b.py").write_text(
        "from pkg.a import value\nimport os\n\nvalue = value + 1\n",
        encoding="utf-8",
    )

    analysis = DependencyAnalyzer().analyze(package_dir)

    assert analysis.project_root == package_dir
    assert analysis.graph is not None
    assert len(analysis.graph.nodes) >= 2
    assert any(edge.kind == "internal" for edge in analysis.graph.edges)
    assert analysis.graph.cycles
    assert analysis.summary["total_edges"] >= 2


def test_dependency_analyzer_classifies_standard_library_edges(tmp_path: Path) -> None:
    source_dir = tmp_path / "demo"
    source_dir.mkdir()
    (source_dir / "app.py").write_text(
        "import os\nimport os.path\nimport json\nfrom pathlib import Path\n",
        encoding="utf-8",
    )

    analysis = DependencyAnalyzer().analyze(source_dir)

    assert analysis.graph is not None
    assert any(edge.kind == "stdlib" for edge in analysis.graph.edges)
    assert analysis.summary["stdlib_edges"] >= 1
    assert all(
        edge.kind == "stdlib"
        for edge in analysis.graph.edges if edge.import_name in {"os", "os.path", "json", "pathlib"}
    )


def test_dependency_analyzer_distinguishes_external_and_unresolved_imports(tmp_path: Path) -> None:
    package = tmp_path / "demo"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "app.py").write_text(
        "import third_party_package\nfrom .missing_module import value\n",
        encoding="utf-8",
    )

    report = DependencyAnalyzer().analyze(tmp_path)

    assert any(edge.kind == "external" and edge.import_name == "third_party_package" for edge in report.graph.edges)
    assert any(edge.kind == "unresolved" and edge.import_name == ".missing_module" for edge in report.graph.edges)


def test_dependency_analyzer_handles_relative_include_paths(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    include_dir = project_root / "include"
    src_dir = project_root / "src"
    include_dir.mkdir(parents=True)
    src_dir.mkdir()

    (include_dir / "common.h").write_text("#pragma once\n#define VALUE 42\n", encoding="utf-8")
    (src_dir / "main.c").write_text('#include "../include/common.h"\nint main(void) { return VALUE; }\n', encoding="utf-8")

    analysis = DependencyAnalyzer().analyze(project_root)

    assert analysis.graph is not None
    assert any(edge.kind == "internal" and edge.import_name == "../include/common.h" for edge in analysis.graph.edges)


def test_dependency_view_renders_project_graph_nodes_and_edges(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    source_dir = project_root / "src"
    source_dir.mkdir(parents=True)
    (source_dir / "__init__.py").write_text("", encoding="utf-8")
    (source_dir / "main.py").write_text("from .utils import run\n", encoding="utf-8")
    (source_dir / "utils.py").write_text("def run():\n    return 1\n", encoding="utf-8")
    opened_files: list[Path] = []
    view = DependencyView(on_file_navigate=opened_files.append)

    view.set_project_root(project_root)

    scroll_child = view.scroller.get_child()
    assert scroll_child is view.canvas or scroll_child.get_child() is view.canvas
    assert view._mode == "overview"
    assert "src" in {node.group_id for node in view._nodes}
    assert view._edges
    assert any(
        edge.source == "src/main.py" and edge.target == "src/utils.py"
        for edge in view._analysis.graph.edges
    )
    original_zoom = view._zoom
    view.zoom_in()
    assert view._zoom > original_zoom


def test_dependency_analyzer_prunes_generated_directories(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "build" / "nested").mkdir(parents=True)
    (tmp_path / ".git" / "objects").mkdir(parents=True)
    (tmp_path / "src" / "app.py").write_text("import os\n", encoding="utf-8")
    (tmp_path / "build" / "nested" / "generated.py").write_text("import sys\n", encoding="utf-8")
    (tmp_path / ".git" / "objects" / "packed.py").write_text("import json\n", encoding="utf-8")

    report = DependencyAnalyzer().analyze(tmp_path)

    assert [node.relative_path for node in report.graph.nodes] == ["src/app.py"]


def test_dependency_analyzer_resolves_absolute_imports_from_src_layout(tmp_path: Path) -> None:
    package = tmp_path / "src" / "sample"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "consumer.py").write_text(
        "from sample.provider import value\n", encoding="utf-8"
    )
    (package / "provider.py").write_text("value = 1\n", encoding="utf-8")

    report = DependencyAnalyzer().analyze(tmp_path)

    assert any(
        edge.source == "src/sample/consumer.py"
        and edge.target == "src/sample/provider.py"
        and edge.kind == "internal"
        for edge in report.graph.edges
    )


def _sample_graph() -> DependencyGraph:
    paths = {
        "src/a.py": Path("/project/src/a.py"),
        "src/b.py": Path("/project/src/b.py"),
        "src/c.py": Path("/project/src/c.py"),
        "include/b.h": Path("/project/include/b.h"),
    }
    nodes = [
        DependencyNode(node_id=key, relative_path=key, display_name=Path(key).name,
                       module_name=key.replace("/", "."), file_path=value)
        for key, value in paths.items()
    ]
    edges = [
        DependencyEdge("src/a.py", "src/b.py", "internal", "b", 1),
        DependencyEdge("src/b.py", "src/c.py", "internal", "c", 2),
        DependencyEdge("src/c.py", "src/a.py", "internal", "a", 3),
        DependencyEdge("include/b.h", "src/b.py", "internal", "../src/b.py", 4),
        DependencyEdge("src/a.py", "include/b.h", "internal", "b.h", 5),
    ]
    return DependencyGraph(nodes=nodes, edges=edges, cycles=[["src/a.py", "src/b.py", "src/c.py"]])


def test_dependency_explorer_traversal_is_depth_limited_and_cycle_safe() -> None:
    graph = _sample_graph()
    model = DependencyExplorerModel(graph)

    depth_one = model.neighborhood("src/a.py", direction="outgoing", depth=1)
    depth_two = model.neighborhood("src/a.py", direction="outgoing", depth=2)
    all_reachable = model.neighborhood("src/a.py", direction="outgoing", depth=None)

    assert depth_one.node_depths == {
        "src/a.py": 0,
        "src/b.py": 1,
        "include/b.h": 1,
    }
    assert set(depth_two.node_depths) == {
        "src/a.py", "src/b.py", "src/c.py", "include/b.h"
    }
    assert set(all_reachable.node_depths) == {
        "src/a.py", "src/b.py", "src/c.py", "include/b.h"
    }
    assert len(all_reachable.edge_indices) == 5
    counts = model.node_counts("src/a.py")
    assert counts["circular"] is True
    assert counts["direct_dependencies"] == 2


def test_dependency_explorer_filters_and_bundles_without_mutating_graph() -> None:
    graph = _sample_graph()
    original_edges = list(graph.edges)
    model = DependencyExplorerModel(graph)

    outgoing = model.filter_edges(
        selected_node_id="src/a.py", direction="outgoing", kind="internal"
    )
    bundles = model.bundle_edges(grouping="directory", edge_indices=outgoing)

    assert outgoing == (0, 4)
    assert len(bundles) == 2
    assert {bundle.edge_indices for bundle in bundles} == {(0,), (4,)}
    headers = model.filter_edges(file_type="header")
    assert headers == (4,)
    assert model.filter_edges(
        selected_node_id="src/a.py", direction="outgoing", kind="internal", file_type="header"
    ) == (4,)
    assert model.filter_edges(
        selected_node_id="src/b.py", direction="incoming", kind="internal"
    ) == (0, 3)
    assert model.filter_edges(cycles_only=True) == (0, 1, 2)
    all_bundled_indices = [
        index for bundle in model.bundle_edges("directory") for index in bundle.edge_indices
    ]
    assert sorted(all_bundled_indices) == list(range(len(graph.edges)))
    assert len(set(all_bundled_indices)) == len(graph.edges)
    assert model.relationship("src/a.py → src/b.py") == (0,)
    assert graph.edges == original_edges


def test_directory_projection_aggregates_real_cross_directory_edges(tmp_path: Path) -> None:
    directories = [
        "kernel/arch/x86", "kernel/memory", "drivers/memory", "empty",
    ]
    files = [
        "root.c", "kernel/cpu.c", "kernel/scheduler.c", "kernel/memory/paging.c",
        "kernel/memory/heap.c", "drivers/keyboard.c", "drivers/memory/cache.c",
    ]
    for directory in directories:
        (tmp_path / directory).mkdir(parents=True, exist_ok=True)
    for relative in files:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")

    graph_nodes = [
        DependencyNode(
            node_id=relative,
            relative_path=relative,
            display_name=Path(relative).name,
            module_name=None,
            file_path=tmp_path / relative,
        )
        for relative in files
    ]
    graph_edges = [
        DependencyEdge("kernel/cpu.c", "kernel/memory/paging.c", "internal", "paging", 1),
        DependencyEdge("kernel/scheduler.c", "kernel/memory/heap.c", "internal", "heap", 2),
        DependencyEdge("drivers/keyboard.c", "kernel/cpu.c", "internal", "cpu", 3),
        DependencyEdge("kernel/cpu.c", "kernel/scheduler.c", "internal", "scheduler", 4),
        DependencyEdge("root.c", "drivers/memory/cache.c", "internal", "cache", 5),
    ]
    graph = DependencyGraph(nodes=graph_nodes, edges=graph_edges)
    model = DependencyExplorerModel(graph)

    projection = model.directory_projection(tmp_path)

    assert isinstance(projection, DependencyDirectoryProjection)
    assert {node.node_id for node in projection.nodes} >= {
        ".", "kernel", "kernel/arch", "kernel/arch/x86", "kernel/memory",
        "drivers", "drivers/memory", "empty",
    }
    assert len({node.node_id for node in projection.nodes}) == len(projection.nodes)
    assert projection.node_by_id["kernel/memory"].file_count == 2
    assert projection.node_by_id["kernel"].file_count == 4
    assert set(projection.node_by_id["kernel"].file_ids) == {
        "kernel/cpu.c", "kernel/scheduler.c", "kernel/memory/paging.c",
        "kernel/memory/heap.c",
    }
    assert projection.node_by_id["empty"].file_count == 0
    assert projection.node_by_id["kernel/memory"].parent_id == "kernel"
    assert projection.node_by_id["drivers/memory"].parent_id == "drivers"
    assert len(projection.edge_by_pair[("kernel", "kernel/memory")].edge_indices) == 2
    assert projection.edge_by_pair[("drivers", "kernel")].edge_indices == (2,)
    assert projection.edge_by_pair[(".", "drivers/memory")].edge_indices == (4,)
    assert all(edge.source_id != edge.target_id for edge in projection.edges)
    assert sum(len(edge.edge_indices) for edge in projection.edges) == 4
    assert len(graph.edges) == 5


def test_dependency_view_switches_between_file_and_directory_projections(tmp_path: Path) -> None:
    (tmp_path / "kernel" / "memory").mkdir(parents=True)
    (tmp_path / "drivers").mkdir()
    (tmp_path / "empty").mkdir()
    (tmp_path / "kernel" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "kernel" / "memory" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "kernel" / "main.py").write_text(
        "from .memory.page import page\nfrom drivers.net import send\n", encoding="utf-8"
    )
    (tmp_path / "kernel" / "scheduler.py").write_text(
        "from .memory.page import page\n", encoding="utf-8"
    )
    (tmp_path / "kernel" / "memory" / "page.py").write_text("def page():\n    return 1\n", encoding="utf-8")
    (tmp_path / "drivers" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "drivers" / "net.py").write_text(
        "from kernel.main import page\n", encoding="utf-8"
    )
    view = DependencyView()

    view.set_project_root(tmp_path)
    source_graph = view._model.graph
    original_edges = list(source_graph.edges)

    assert view._view_kind == "all"
    assert view.view_select.get_selected() == 0
    assert len(source_graph.nodes) == 7

    view.view_select.set_selected(1)

    assert view._view_kind == "directories"
    assert all(node.is_directory for node in view._nodes)
    assert {node.group_id for node in view._nodes} >= {
        ".", "kernel", "kernel/memory", "drivers", "empty",
    }
    assert len({node.group_id for node in view._nodes}) == len(view._nodes)
    assert view._directory_projection.edge_by_pair[("kernel", "kernel/memory")].relationship_count == 2
    assert all(edge.source != edge.target for edge in view._edges)

    def click_directory(directory_id: str) -> None:
        node = view._node_by_id[f"@directory:{directory_id}"]
        origin_x, origin_y = view._origin()
        view._on_click(
            None,
            1,
            (node.x + view.NODE_WIDTH / 2) * view._zoom + origin_x + view._pan[0],
            (node.y + view.NODE_HEIGHT / 2) * view._zoom + origin_y + view._pan[1],
        )

    click_directory("kernel")
    assert "kernel" in view._collapsed_directories
    assert "@directory:kernel/memory" not in view._node_by_id
    click_directory("kernel")
    assert "kernel" not in view._collapsed_directories
    assert "@directory:kernel/memory" in view._node_by_id
    view._on_clear_pick(None)

    view._on_pick_selected(None, "directory", "kernel")

    assert view._view_kind == "directories"
    assert view._node_by_id["@directory:kernel"].selected
    assert {
        (edge.source, edge.target) for edge in view._edges
    } == {("@directory:kernel", "@directory:drivers"), ("@directory:drivers", "@directory:kernel")}

    view._on_clear_pick(None)
    assert view._view_kind == "directories"
    assert view._picked_item is None
    assert len(view._edges) == len(view._directory_projection.edges)

    view._on_pick_selected(None, "file", "kernel/main.py")
    assert view._view_kind == "all"
    assert "kernel/main.py" in view._node_by_id
    assert view._selected_node == "kernel/main.py"
    pan_before_clear = view._pan
    view._on_clear_pick(None)
    assert view._view_kind == "directories"
    assert view._picked_item is None
    assert view._pan == pan_before_clear

    view.view_select.set_selected(0)
    view._on_pick_selected(None, "directory", "kernel")
    assert view._view_kind == "all"
    assert {
        "kernel/main.py", "kernel/scheduler.py", "kernel/memory/page.py"
    } <= set(view._node_by_id)
    assert view._selected_sources == set(
        view._directory_projection.node_by_id["kernel"].file_ids
    )
    view._on_clear_pick(None)
    assert view._view_kind == "all"
    assert source_graph.edges == original_edges


def test_dependency_picker_searches_full_file_and_directory_paths(tmp_path: Path) -> None:
    nested = tmp_path / "kernel" / "memory"
    nested.mkdir(parents=True)
    (nested / "paging.c").write_text("", encoding="utf-8")
    view = DependencyView()
    view.set_project_root(tmp_path)

    view.pick_search.set_text("kernel/memory")
    directory_labels = []
    child = view.pick_results.get_first_child()
    while child is not None:
        button = child.get_last_child() if child.get_first_child() is not None else None
        label = button.get_child() if button is not None else None
        if label is not None and hasattr(label, "get_text"):
            directory_labels.append(label.get_text())
        child = child.get_next_sibling()
    assert "kernel/memory/" in directory_labels

    view.pick_search.set_text("paging.c")
    file_labels = []
    child = view.pick_results.get_first_child()
    while child is not None:
        button = child.get_last_child() if child.get_first_child() is not None else None
        label = button.get_child() if button is not None else None
        if label is not None and hasattr(label, "get_text"):
            file_labels.append(label.get_text())
        child = child.get_next_sibling()
    assert "kernel/memory/paging.c" in file_labels


def test_dependency_view_progressively_discloses_group_and_node_relationships(tmp_path: Path) -> None:
    package = tmp_path / "pkg"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "a.py").write_text(
        "from .b import value\nfrom .c import value\n", encoding="utf-8"
    )
    (package / "b.py").write_text("from .a import value\n", encoding="utf-8")
    (package / "c.py").write_text("from .b import value\n", encoding="utf-8")
    view = DependencyView()

    view.set_project_root(tmp_path)

    assert view._mode == "overview"
    assert view._edges
    assert all(edge.bundle_id is not None for edge in view._edges)
    assert sum(len(edge.indices) for edge in view._edges) == len(view._model.graph.edges)

    view._expanded_groups.add("pkg")
    view._render()
    assert "pkg/a.py" in view._node_by_id
    view._show_group_details("pkg")
    view.detail_search.set_text("a.py")
    assert len(list(view.details_list)) == 1
    view._on_detail_file(None, "pkg/a.py")
    assert view._mode == "explore"
    assert {
        (view._model.graph.edges[index].source, view._model.graph.edges[index].target)
        for edge in view._edges for index in edge.indices
    } == {
        ("pkg/a.py", "pkg/b.py"),
        ("pkg/a.py", "pkg/c.py"),
        ("pkg/b.py", "pkg/a.py"),
    }
    outbound = next(edge for edge in view._edges if edge.source == "pkg/a.py")
    inbound = next(edge for edge in view._edges if edge.target == "pkg/a.py")
    assert view._edge_color(outbound) == (0.98, 0.99, 1.0)
    assert view._edge_color(inbound) == (0.82, 0.34, 0.72)
    assert view._node_by_id["pkg/b.py"].outgoing_target
    assert view._node_by_id["pkg/c.py"].outgoing_target
    outgoing_edges = [edge for edge in view._edges if edge.source == "pkg/a.py"]
    outgoing_starts = {
        view._routes[view._edges.index(edge)][0] for edge in outgoing_edges
    }
    assert len(outgoing_starts) == 2
    assert all(view._edge_color(edge) == (0.98, 0.99, 1.0) for edge in outgoing_edges)

    view.direction.set_selected(2)
    incoming = {
        (view._model.graph.edges[index].source, view._model.graph.edges[index].target)
        for edge in view._edges for index in edge.indices
    }
    assert incoming == {("pkg/b.py", "pkg/a.py")}

    view.mode_select.set_selected(2)
    assert view._mode == "full"
    bundle = next(edge for edge in view._edges if edge.bundle_id is not None)
    bundle_index = view._edges.index(bundle)
    point = view._routes[bundle_index][8]
    origin = view._origin()
    view._on_click(
        None,
        1,
        point[0] * view._zoom + origin[0] + view._pan[0],
        point[1] * view._zoom + origin[1] + view._pan[1],
    )
    assert bundle.bundle_id in view._expanded_bundles

    expanded_index = next(
        index for index, edge in enumerate(view._edges)
        if edge.bundle_id == bundle.bundle_id and not edge.bundle_summary
    )
    point = view._routes[expanded_index][8]
    origin = view._origin()
    view._on_click(
        None,
        1,
        point[0] * view._zoom + origin[0] + view._pan[0],
        point[1] * view._zoom + origin[1] + view._pan[1],
    )
    assert bundle.bundle_id not in view._expanded_bundles
    assert bundle.bundle_id in view._collapsed_bundles

    view._collapsed_bundles.clear()
    view.zoom_in()
    view.zoom_in()
    assert any(not edge.bundle_summary for edge in view._edges)
    view.zoom_out()
    assert all(edge.bundle_summary for edge in view._edges)

    view._expanded_bundles.add(bundle.bundle_id)
    view._render()
    assert all(edge.bundle_id is not None and not edge.bundle_summary for edge in view._edges)
    assert sum(len(edge.indices) for edge in view._edges) == len(view._model.graph.edges)


def test_dependency_view_search_and_composed_filters(tmp_path: Path) -> None:
    package = tmp_path / "pkg"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "a.py").write_text("from .b import value\n", encoding="utf-8")
    (package / "b.py").write_text("value = 1\n", encoding="utf-8")
    view = DependencyView()
    view.set_project_root(tmp_path)

    view.search.set_text("pkg/a.py -> pkg/b.py")
    view._on_search(view.search)

    assert view._mode == "explore"
    assert view._selected_node == "pkg/a.py"
    assert "pkg/a.py -> pkg/b.py" in view.details.get_text()
    assert view._focus_edges

    view.kind.set_selected(1)
    assert all(view._model.graph.edges[index].kind == "internal" for edge in view._edges for index in edge.indices)
    view.cycles.set_active(True)
    assert not view._edges
    view.search.set_text("pkg/a.py → pkg/b.py")
    view._on_search(view.search)
    assert view._edges
    assert not view.cycles.get_active()
    view.search.set_text("missing.py -> nowhere.py")
    view._on_search(view.search)
    assert "No matching relationship" in view.details.get_text()


def test_dependency_view_caps_dense_overview_but_preserves_full_map(tmp_path: Path) -> None:
    package_names = [f"pkg{index:02d}" for index in range(16)]
    for package_name in package_names:
        package = tmp_path / package_name
        package.mkdir()
        (package / "__init__.py").write_text("", encoding="utf-8")
        imports = [
            f"import {target}.module"
            for target in package_names if target != package_name
        ]
        (package / "module.py").write_text("\n".join(imports), encoding="utf-8")
    view = DependencyView()

    view.set_project_root(tmp_path)

    assert len(view._model.graph.edges) == 16 * 15
    assert len(view._edges) == view._MAX_OVERVIEW_BUNDLES
    assert "showing 120 of 240" in view.status.get_text()

    view.mode_select.set_selected(2)

    assert sum(len(edge.indices) for edge in view._edges) == 16 * 15
