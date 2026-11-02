from __future__ import annotations

from ..menu_context import MenuContext


def is_enabled(context: MenuContext) -> bool:
    return _is_project_item(context)


def _is_project_item(context: MenuContext) -> bool:
    if context.kind != "explorer" or context.path is None or context.project_root is None:
        return False
    try:
        path = context.path.resolve()
        root = context.project_root.resolve()
        path.relative_to(root)
    except (OSError, ValueError):
        return False
    return path != root


def run(context: MenuContext) -> None:
    if is_enabled(context) and context.open_action_menu is not None:
        context.open_action_menu(
            "rename", context, context.action_anchor or context.widget
        )