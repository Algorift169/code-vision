from __future__ import annotations

from pathlib import Path

from .graph_collector import GraphCollector
from .graph_renderer import GraphRenderer


class AssetManager:
    """Manage temporary graph assets used by export reports."""

    def collect_and_render(self, analysis: dict, assets_dir: Path) -> dict[str, list[str]]:
        assets_dir.mkdir(parents=True, exist_ok=True)
        collected = GraphCollector().collect(analysis)
        rendered: dict[str, list[str]] = {name: [] for name in collected}
        flowcharts = collected.get("flowcharts")
        if isinstance(flowcharts, list):
            try:
                paths = GraphRenderer().render_flowcharts(flowcharts, assets_dir / "flowcharts")
                rendered["flowcharts"] = [str(path) for path in paths]
            except (ImportError, OSError, RuntimeError, TypeError, ValueError) as error:
                rendered["flowcharts"] = [f"unavailable: {error}"]
        return rendered
