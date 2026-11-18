from __future__ import annotations

from . import (
    clear_screen,
    copy,
    forward_to_space,
    remove,
    rename_box,
    show_complexity,
)

ANALYSIS_PANEL_ACTIONS = (
    ("panel-copy", "Copy", "edit-copy-symbolic", copy),
    ("forward-to-space", "Forward to Space", "go-next-symbolic", forward_to_space),
    (
        "show-complexity",
        "Show Complexity",
        "view-list-symbolic",
        show_complexity,
    ),
    ("rename-box", "Rename Box", "edit-rename-symbolic", rename_box),
    ("clear-screen", "Clear Screen", "edit-clear-symbolic", clear_screen),
    ("panel-remove", "Remove", "edit-delete-symbolic", remove),
)

ANALYSIS_PANEL_ACTION_ORDER = tuple(
    action_id for action_id, _label, _icon, _action in ANALYSIS_PANEL_ACTIONS
)
