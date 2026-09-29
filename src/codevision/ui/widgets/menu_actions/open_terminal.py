from __future__ import annotations

from ..menu_context import MenuContext


def is_enabled(context: MenuContext) -> bool:
    service = context.terminal_service
    return (
        service is not None
        and service.is_available
        and context.open_terminal is not None
        and context.directory.is_dir()
    )


def run(context: MenuContext) -> None:
    if context.open_terminal is not None:
        context.open_terminal()