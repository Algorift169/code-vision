from __future__ import annotations

from . import (
    change_color,
    clear_screen,
    copy,
    duplicate_box,
    forward_to_space,
    forward_full_graph,
    remove,
    rename_box,
    select_all,
    select_multiple,
    show_complexity,
)

ANALYSIS_PANEL_ACTIONS = (
    ("panel-copy", "Copy", "edit-copy-symbolic", copy),
    ("panel-select-all", "Select All", "edit-select-all-symbolic", select_all),
    (
        "panel-select-multiple",
        "Select Multiple",
        "edit-select-all-symbolic",
        select_multiple,
    ),
    ("forward-to-space", "Forward to Space", "go-next-symbolic", forward_to_space),
    (
        "forward-full-graph",
        "Forward Full Graph to Space",
        "go-next-symbolic",
        forward_full_graph,
    ),
    (
        "show-complexity",
        "Show Complexity",
        "view-list-symbolic",
        show_complexity,
    ),
    ("rename-box", "Rename", "edit-rename-symbolic", rename_box),
    ("clear-screen", "Clear Screen", "edit-clear-symbolic", clear_screen),
    ("panel-remove", "Remove", "edit-delete-symbolic", remove),
    ("change-color", "Change Color", "applications-graphics-symbolic", change_color),
    ("duplicate-box", "Duplicate Box", "edit-copy-symbolic", duplicate_box),
)

ANALYSIS_PANEL_ACTION_ORDER = tuple(
    action_id for action_id, _label, _icon, _action in ANALYSIS_PANEL_ACTIONS
)
