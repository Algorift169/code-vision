from __future__ import annotations

from ..menu_context import MenuContext


def is_enabled(context: MenuContext) -> bool:
    service = context.terminal_service
    return service is not None and service.has_running_terminal


def run(context: MenuContext) -> None:
    if context.terminal_service is not None:
        context.terminal_service.kill_latest()