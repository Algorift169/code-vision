from __future__ import annotations

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("GLib", "2.0")
gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, GLib, Gtk

from ..theme import THEMES, TRANSPARENT_THEME_ID


class ThemeMenu(Gtk.Box):
    """Overlay menu for choosing and applying an application theme."""

    def __init__(self, window: object, overlay: Gtk.Overlay) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        self._window = window
        self._overlay = overlay
        self.set_name("codevision-context-menu")
        self.add_css_class("context-menu-popup")
        self.add_css_class("context-menu-content")
        self.add_css_class("codevision-context-menu")
        self.set_halign(Gtk.Align.START)
        self.set_valign(Gtk.Align.START)
        self.set_visible(False)
        self._theme_items: dict[str, tuple[Gtk.Button, Gtk.Label]] = {}

        theme_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        for theme in THEMES:
            button = Gtk.Button()
            button.set_has_frame(False)
            button.set_halign(Gtk.Align.FILL)
            button.add_css_class("context-menu-item")

            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            check = Gtk.Label(label="")
            check.set_width_chars(2)
            row.append(check)

            label = Gtk.Label(label=theme.name)
            label.set_halign(Gtk.Align.START)
            label.set_hexpand(True)
            label.set_xalign(0)
            row.append(label)
            button.set_child(row)
            button.connect("clicked", self._on_theme_selected, theme.theme_id)
            theme_list.append(button)
            self._theme_items[theme.theme_id] = (button, check)

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_propagate_natural_height(True)
        scroller.set_max_content_height(360)
        scroller.set_child(theme_list)
        self.append(scroller)

        self._transparency_panel = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=6
        )
        self._transparency_panel.set_margin_start(10)
        self._transparency_panel.set_margin_end(10)
        self._transparency_panel.set_margin_top(6)
        self._transparency_panel.set_margin_bottom(8)
        self._transparency_panel.set_visible(False)

        transparency_header = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=8
        )
        transparency_title = Gtk.Label(label="Window transparency")
        transparency_title.set_halign(Gtk.Align.START)
        transparency_title.set_hexpand(True)
        self._transparency_label = Gtk.Label()
        transparency_header.append(transparency_title)
        transparency_header.append(self._transparency_label)
        self._transparency_panel.append(Gtk.Separator())
        self._transparency_panel.append(transparency_header)

        self._transparency_scale = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL, 0, 90, 5
        )
        self._transparency_scale.set_hexpand(True)
        self._transparency_scale.set_draw_value(False)
        self._transparency_scale.connect(
            "value-changed", self._on_transparency_changed
        )
        self._transparency_panel.append(self._transparency_scale)

        apply_button = Gtk.Button(label="Apply")
        apply_button.set_halign(Gtk.Align.END)
        apply_button.add_css_class("context-menu-item")
        apply_button.connect("clicked", self._on_transparency_applied)
        self._transparency_panel.append(apply_button)
        self.append(self._transparency_panel)

        overlay.add_overlay(self)
        overlay.set_measure_overlay(self, False)

        dismiss = Gtk.GestureClick.new()
        dismiss.set_button(1)
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

    def popup_at(self, anchor: Gtk.Widget) -> None:
        ok, bounds = anchor.compute_bounds(self._overlay)
        if ok:
            x = max(0, int(bounds.get_x() + bounds.get_width()))
            y = max(0, int(bounds.get_y()))
            overlay_width = self._overlay.get_width()
            menu_width = max(self.get_width(), 240)
            if overlay_width > 0 and x + menu_width > overlay_width:
                x = max(0, int(bounds.get_x()) - menu_width)
            self.set_margin_start(x)
            self.set_margin_top(y)

        root = self._window
        if hasattr(root, "close_all_menus"):
            root.close_all_menus(except_menu=self)
        self._update_state()
        self._update_transparency_panel()
        self.set_visible(True)

    def _update_state(self) -> None:
        selected_theme = self._window.theme_manager.current_theme
        for theme_id, (_button, check) in self._theme_items.items():
            selected = theme_id == selected_theme
            check.set_text("✓" if selected else "")

    def _update_transparency_panel(self) -> None:
        theme_manager = self._window.theme_manager
        is_transparent = theme_manager.current_theme == TRANSPARENT_THEME_ID
        self._transparency_panel.set_visible(is_transparent)
        if is_transparent:
            percentage = theme_manager.transparency_percent
            self._transparency_scale.set_value(percentage)
            self._transparency_label.set_text(f"{percentage}%")

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
        _state: Gtk.ModifierType,
    ) -> bool:
        if keyval != Gdk.KEY_Escape or not self.get_visible():
            return False
        self.popdown()
        if hasattr(self._window, "close_all_menus"):
            self._window.close_all_menus()
        return True

    def _on_theme_selected(self, _button: Gtk.Button, theme_id: str) -> None:
        theme = next(theme for theme in THEMES if theme.theme_id == theme_id)
        try:
            self._window.set_theme(theme_id)
        except (OSError, GLib.Error, RuntimeError, ValueError) as error:
            self._window.status_label.set_text(f"Could not apply theme: {error}")
            self.popdown()
            return

        self._window.status_label.set_text(f"Theme: {theme.name}")
        if theme_id == TRANSPARENT_THEME_ID:
            self._update_state()
            self._update_transparency_panel()
            return
        self._transparency_panel.set_visible(False)
        self.popdown()

    def _on_transparency_changed(self, scale: Gtk.Scale) -> None:
        percentage = int(round(scale.get_value()))
        self._transparency_label.set_text(f"{percentage}%")
        try:
            self._window.set_transparency_percent(percentage)
        except (OSError, GLib.Error, RuntimeError, ValueError) as error:
            self._window.status_label.set_text(
                f"Could not set transparency: {error}"
            )

    def _on_transparency_applied(self, _button: Gtk.Button) -> None:
        self.popdown()


__all__ = ["ThemeMenu"]
