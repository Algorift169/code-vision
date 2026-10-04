from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gtk

from .menu_actions import (
    copy,
    copy_full_path,
    copy_relative_path,
    change_theme,
    delete,
    kill_terminal,
    new_file,
    open_kong_browser,
    open_terminal,
    paste,
    rename,
    select,
    select_all,
)
from .menu_context import MenuContext


class ContextMenu(Gtk.Popover):
    """Reusable context popover that delegates work to focused action modules."""

    _ACTIONS = (
        ("new-file", "New File", "document-new-symbolic", new_file),
        ("open-terminal", "Open Terminal", "utilities-terminal-symbolic", open_terminal),
        ("change-theme", "Change Theme", "preferences-desktop-theme-symbolic", change_theme),
        ("rename", "Rename", "edit-rename-symbolic", rename),
        ("delete", "Delete", "edit-delete-symbolic", delete),
        ("copy", "Copy", "edit-copy-symbolic", copy),
        ("paste", "Paste", "edit-paste-symbolic", paste),
        ("copy-full-path", "Copy Full Path", "document-open-symbolic", copy_full_path),
        ("copy-relative-path", "Copy Relative Path", "folder-symbolic", copy_relative_path),
        ("select", "Select", "edit-select-all-symbolic", select),
        ("select-all", "Select All", "edit-select-all-symbolic", select_all),
        ("kong-browser", "Kong Browser", "network-transmit-symbolic", open_kong_browser),
        ("kill-terminal", "Kill Terminal", "process-stop-symbolic", kill_terminal),
    )

    def __init__(
        self,
        parent: Gtk.Widget,
        context_at: Callable[[float, float], MenuContext],
    ) -> None:
        super().__init__()
        self.set_name("codevision-context-menu")
        self.set_has_arrow(False)
        self.set_autohide(True)
        self.add_css_class("codevision-context-menu")
        self._context_at = context_at
        self._context: MenuContext | None = None
        self._enabled = True
        self._items: dict[str, tuple[Gtk.Button, object]] = {}

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        content.add_css_class("context-menu-content")
        for action_id, label, icon_name, action in self._ACTIONS:
            if action_id in {"copy", "select"}:
                content.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
            button = Gtk.Button()
            button.set_has_frame(False)
            button.set_halign(Gtk.Align.FILL)
            button.add_css_class("context-menu-item")
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            row.append(Gtk.Image.new_from_icon_name(icon_name))
            title = Gtk.Label(label=label)
            title.set_halign(Gtk.Align.START)
            title.set_hexpand(True)
            row.append(title)
            button.set_child(row)
            button.connect("clicked", self._on_action_clicked, action_id)
            content.append(button)
            self._items[action_id] = (button, action)
        self.set_child(content)
        self.set_parent(parent)

        gesture = Gtk.GestureClick.new()
        gesture.set_button(Gdk.BUTTON_SECONDARY)
        gesture.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        gesture.connect("pressed", self._on_pressed)
        parent.add_controller(gesture)
        self._gesture = gesture

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def _on_pressed(
        self,
        _gesture: Gtk.GestureClick,
        _press_count: int,
        x: float,
        y: float,
    ) -> None:
        if not self._enabled:
            return
        self._context = self._context_at(x, y)
        self._update_state()
        pointing = Gdk.Rectangle()
        pointing.x = int(x)
        pointing.y = int(y)
        pointing.width = 1
        pointing.height = 1
        self.set_pointing_to(pointing)
        self.popup()

    def _update_state(self) -> None:
        if self._context is None:
            return
        for button, action in self._items.values():
            button.set_sensitive(action.is_enabled(self._context))

    def _on_action_clicked(self, _button: Gtk.Button, action_id: str) -> None:
        context = self._context
        if context is None:
            return
        action = self._items[action_id][1]
        self.popdown()
        try:
            action.run(context)
        except (OSError, RuntimeError, ValueError) as error:
            if context.set_status is not None:
                context.set_status(str(error))
