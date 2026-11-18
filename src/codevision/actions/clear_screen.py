from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..ui.widgets.menu_context import MenuContext


def is_enabled(context: MenuContext) -> bool:
    return context.kind == "analysis-panel"


def run(_context: MenuContext) -> None:
    return None
