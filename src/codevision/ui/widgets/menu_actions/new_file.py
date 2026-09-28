from __future__ import annotations

from ..menu_context import MenuContext


def is_enabled(context: MenuContext) -> bool:
    return context.create_file is not None


def run(context: MenuContext) -> None:
    if context.create_file is not None:
        context.create_file()