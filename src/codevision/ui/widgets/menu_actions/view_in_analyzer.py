from __future__ import annotations

from ..menu_context import MenuContext


def is_enabled(context: MenuContext) -> bool:
    return (
        context.kind == "explorer"
        and context.path is not None
        and context.path.is_file()
        and context.view_in_analyzer is not None
    )


def run(context: MenuContext) -> None:
    if is_enabled(context):
        context.view_in_analyzer(context.path)