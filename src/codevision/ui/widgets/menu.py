from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gtk

from .menu_actions import (
    change_theme,
    copy,
    copy_full_path,
    copy_relative_path,
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
from .symbolic_icon import create_symbolic_icon


class ContextMenu(Gtk.Box):
    """Reusable overlay context menu that delegates to focused action modules."""

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
        overlay: Gtk.Overlay,
        event_parent: Gtk.Widget,
        context_at: Callable[[float, float], MenuContext],
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        self.set_name("codevision-context-menu")
        self.add_css_class("context-menu-popup")
        self.add_css_class("context-menu-content")
        self.set_halign(Gtk.Align.START)
        self.set_valign(Gtk.Align.START)
        self.set_visible(False)
        self.add_css_class("codevision-context-menu")
        self._overlay = overlay
        self._event_parent = event_parent
        self._context_at = context_at
        self._context: MenuContext | None = None
        self._enabled = True
        self._items: dict[str, tuple[Gtk.Button, object]] = {}

        for action_id, label, icon_name, action in self._ACTIONS:
            if action_id in {"copy", "select"}:
                self.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
            button = Gtk.Button()
            button.set_has_frame(False)
            button.set_halign(Gtk.Align.FILL)
            button.add_css_class("context-menu-item")
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            icon = create_symbolic_icon(icon_name, "context-menu-icon")
            row.append(icon)
            title = Gtk.Label(label=label)
            title.set_halign(Gtk.Align.START)
            title.set_hexpand(True)
            row.append(title)
            button.set_child(row)
            button.connect("clicked", self._on_action_clicked, action_id)
            self.append(button)
            self._items[action_id] = (button, action)
        overlay.add_overlay(self)
        overlay.set_measure_overlay(self, False)

        gesture = Gtk.GestureClick.new()
        gesture.set_button(Gdk.BUTTON_SECONDARY)
        gesture.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        gesture.connect("pressed", self._on_pressed)
        event_parent.add_controller(gesture)
        self._gesture = gesture

        dismiss_gesture = Gtk.GestureClick.new()
        dismiss_gesture.set_button(Gdk.BUTTON_PRIMARY)
        dismiss_gesture.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        dismiss_gesture.connect("pressed", self._on_dismiss_pressed)
        event_parent.add_controller(dismiss_gesture)
        self._dismiss_gesture = dismiss_gesture

        keys = Gtk.EventControllerKey.new()
        keys.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        keys.connect("key-pressed", self._on_key_pressed)
        event_parent.add_controller(keys)
        self._key_controller = keys

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def get_active(self) -> bool:
        return self.get_visible()

    def popdown(self) -> None:
        if self.get_visible():
            self.set_visible(False)

    def _on_pressed(
        self,
        gesture: Gtk.GestureClick,
        _press_count: int,
        x: float,
        y: float,
    ) -> None:
        if not self._enabled:
            if gesture is not None:
                gesture.set_state(Gtk.EventSequenceState.DENIED)
            return
        root = self._event_parent.get_root() if hasattr(self, "_event_parent") else None
        if root is not None and hasattr(root, "close_all_menus"):
            root.close_all_menus(except_menu=self)
        self._context = self._context_at(x, y)
        self._update_state()
        self.set_margin_start(int(x))
        self.set_margin_top(int(y))
        self.set_visible(True)
        if gesture is not None:
            gesture.set_state(Gtk.EventSequenceState.CLAIMED)

    def _on_dismiss_pressed(
        self,
        gesture: Gtk.GestureClick,
        _press_count: int,
        _x: float,
        _y: float,
    ) -> None:
        if self.get_visible():
            self.set_visible(False)
        root = self._event_parent.get_root() if hasattr(self, "_event_parent") else None
        click_inside_menu = (
            root is not None
            and hasattr(root, "is_click_inside_open_menu")
            and root.is_click_inside_open_menu(self._event_parent, _x, _y)
        )
        click_on_menu_button = (
            root is not None
            and hasattr(root, "is_click_on_active_menu_button")
            and root.is_click_on_active_menu_button(self._event_parent, _x, _y)
        )
        if (
            root is not None
            and hasattr(root, "close_all_menus")
            and not click_inside_menu
            and not click_on_menu_button
        ):
            root.close_all_menus(except_menu=self)
        if gesture is not None:
            gesture.set_state(Gtk.EventSequenceState.DENIED)

    def _on_key_pressed(
        self,
        _controller: Gtk.EventControllerKey,
        keyval: int,
        _keycode: int,
        _state: Gdk.ModifierType,
    ) -> bool:
        """Dismiss the context menu when the Escape key is pressed."""
        if keyval == Gdk.KEY_Escape:
            handled = False
            if self.get_visible():
                self.set_visible(False)
                handled = True
            root = self._event_parent.get_root() if hasattr(self, "_event_parent") else None
            if (
                root is not None
                and hasattr(root, "close_all_menus")
                and root.close_all_menus()
            ):
                handled = True
            return handled
        return False

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
        context.action_anchor = _button
        if action_id == "change-theme" and context.open_theme_menu is not None:
            try:
                context.open_theme_menu(_button)
            except (OSError, RuntimeError, ValueError) as error:
                if context.set_status is not None:
                    context.set_status(str(error))
        self.set_visible(False)
        if action_id == "change-theme":
            return
        try:
            action.run(context)
        except (OSError, RuntimeError, ValueError) as error:
            if context.set_status is not None:
                context.set_status(str(error))
