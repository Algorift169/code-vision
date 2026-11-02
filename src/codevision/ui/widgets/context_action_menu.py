from __future__ import annotations

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gtk

from ...services.file_operations import FileOperationService
from ...services.new_file import NewFileService
from .menu_context import MenuContext


class ContextActionMenu(Gtk.Box):
    """In-window forms for context-menu actions that need user input."""

    def __init__(self, window: object, overlay: Gtk.Overlay) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self._window = window
        self._overlay = overlay
        self._file_service = NewFileService()
        self._operation_service = FileOperationService()
        self._action = ""
        self._context: MenuContext | None = None
        self._entry: Gtk.Entry | None = None
        self._error_label: Gtk.Label | None = None
        self.set_name("codevision-context-menu")
        self.add_css_class("context-menu-popup")
        self.add_css_class("context-menu-content")
        self.add_css_class("codevision-context-menu")
        self.set_halign(Gtk.Align.START)
        self.set_valign(Gtk.Align.START)
        self.set_visible(False)

        overlay.add_overlay(self)
        overlay.set_measure_overlay(self, False)

        dismiss = Gtk.GestureClick.new()
        dismiss.set_button(Gdk.BUTTON_PRIMARY)
        dismiss.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        dismiss.connect("pressed", self._on_overlay_pressed)
        overlay.add_controller(dismiss)
        self._dismiss_gesture = dismiss

        keys = Gtk.EventControllerKey.new()
        keys.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        keys.connect("key-pressed", self._on_key_pressed)
        overlay.add_controller(keys)
        self._key_controller = keys

    def get_active(self) -> bool:
        return self.get_visible()

    def popdown(self) -> None:
        self.set_visible(False)

    def popup_for(
        self, action: str, context: MenuContext, anchor: Gtk.Widget
    ) -> None:
        self._action = action
        self._context = context
        self._build_form()

        ok, bounds = anchor.compute_bounds(self._overlay)
        if ok:
            x = max(0, int(bounds.get_x() + bounds.get_width()))
            y = max(0, int(bounds.get_y()))
            overlay_width = self._overlay.get_width()
            menu_width = max(self.get_width(), 260)
            if overlay_width > 0 and x + menu_width > overlay_width:
                x = max(0, int(bounds.get_x()) - menu_width)
            self.set_margin_start(x)
            self.set_margin_top(y)

        if hasattr(self._window, "close_all_menus"):
            self._window.close_all_menus(except_menu=self)
        self.set_visible(True)
        if self._entry is not None:
            self._entry.grab_focus()
            if action == "rename":
                self._entry.select_region(0, -1)

    def _build_form(self) -> None:
        child = self.get_first_child()
        while child is not None:
            following = child.get_next_sibling()
            self.remove(child)
            child = following

        context = self._context
        if context is None:
            return

        title, confirm_text = {
            "new-file": ("New File", "Create"),
            "rename": ("Rename", "Rename"),
            "delete": ("Delete", "Delete"),
        }[self._action]
        heading = Gtk.Label(label=title)
        heading.set_halign(Gtk.Align.START)
        heading.add_css_class("section-title")
        self.append(heading)

        self._entry = None
        if self._action == "delete":
            label = Gtk.Label(
                label=f"Delete '{context.path.name}'? This cannot be undone."
            )
            label.set_wrap(True)
            label.set_halign(Gtk.Align.START)
            self.append(label)
        else:
            entry = Gtk.Entry()
            entry.set_hexpand(True)
            entry.set_activates_default(True)
            if self._action == "new-file":
                entry.set_placeholder_text("File name")
            elif context.path is not None:
                entry.set_text(context.path.name)
            entry.connect("activate", lambda _entry: self._on_confirm())
            self.append(entry)
            self._entry = entry

        self._error_label = Gtk.Label()
        self._error_label.set_halign(Gtk.Align.START)
        self._error_label.set_wrap(True)
        self._error_label.add_css_class("explorer-error")
        self._error_label.set_visible(False)
        self.append(self._error_label)

        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        buttons.set_halign(Gtk.Align.END)
        cancel = Gtk.Button(label="Cancel")
        cancel.connect("clicked", lambda _button: self.popdown())
        buttons.append(cancel)

        confirm = Gtk.Button(label=confirm_text)
        confirm.add_css_class(
            "destructive-action" if self._action == "delete" else "suggested-action"
        )
        confirm.connect("clicked", lambda _button: self._on_confirm())
        buttons.append(confirm)
        self.append(buttons)

    def _on_confirm(self) -> None:
        context = self._context
        if context is None:
            return

        try:
            if self._action == "new-file":
                if self._entry is None:
                    return
                path = self._file_service.create(
                    context.directory, self._entry.get_text()
                )
                if context.on_path_created is not None:
                    context.on_path_created(path)
                message = None
            elif self._action == "rename":
                if context.path is None or self._entry is None:
                    return
                path = self._operation_service.rename(
                    context.path, self._entry.get_text()
                )
                if context.on_path_renamed is not None:
                    context.on_path_renamed(context.path, path)
                message = f"Renamed: {path.name}"
            elif self._action == "delete":
                if context.path is None:
                    return
                self._operation_service.delete(context.path)
                if context.on_path_deleted is not None:
                    context.on_path_deleted(context.path)
                message = f"Deleted: {context.path.name}"
            else:
                return
        except (OSError, ValueError) as error:
            if self._error_label is not None:
                self._error_label.set_text(str(error))
                self._error_label.set_visible(True)
            return

        if message is not None and context.set_status is not None:
            context.set_status(message)
        self.popdown()

    def _on_overlay_pressed(
        self,
        gesture: Gtk.GestureClick,
        _press_count: int,
        x: float,
        y: float,
    ) -> None:
        if self.get_visible():
            ok, bounds = self.compute_bounds(self._overlay)
            if ok:
                left = bounds.get_x()
                top = bounds.get_y()
                if (
                    left <= x <= left + bounds.get_width()
                    and top <= y <= top + bounds.get_height()
                ):
                    gesture.set_state(Gtk.EventSequenceState.DENIED)
                    return

            self.popdown()
            if hasattr(self._window, "close_all_menus"):
                self._window.close_all_menus()
        gesture.set_state(Gtk.EventSequenceState.DENIED)

    def _on_key_pressed(
        self,
        _controller: Gtk.EventControllerKey,
        keyval: int,
        _keycode: int,
        _state: Gdk.ModifierType,
    ) -> bool:
        if keyval != Gdk.KEY_Escape or not self.get_visible():
            return False
        self.popdown()
        if hasattr(self._window, "close_all_menus"):
            self._window.close_all_menus()
        return True


__all__ = ["ContextActionMenu"]
