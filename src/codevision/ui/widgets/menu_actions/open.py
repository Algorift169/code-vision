from __future__ import annotations

from ..menu_context import MenuContext


def is_enabled(context: MenuContext) -> bool:
    return (
        context.kind == "explorer"
        and context.path is not None
        and context.path.exists()
        and context.open_path is not None
    )


def run(context: MenuContext) -> None:
    if is_enabled(context):
        context.open_path(context.path)