from __future__ import annotations

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gtk


class OverlayMenuButton(Gtk.Button):
    """Button in the menu bar that toggles an overlay dropdown without Gtk.Popover."""

    def __init__(
        self,
        window: object,
        label: str = "",
        overlay: Gtk.Overlay | None = None,
    ) -> None:
        super().__init__(label=label)
        self.set_has_frame(False)
        self.add_css_class("menu-button")
        self._window = window
        self._overlay: Gtk.Overlay | None = None

        self._popup = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        self._popup.set_name("codevision-context-menu")
        self._popup.add_css_class("context-menu-popup")
        self._popup.add_css_class("context-menu-content")
        self._popup.add_css_class("codevision-context-menu")
        self._popup.set_halign(Gtk.Align.START)
        self._popup.set_valign(Gtk.Align.START)
        self._popup.set_visible(False)
        self._content = self._popup

        resolved_overlay = overlay
        if resolved_overlay is None and hasattr(window, "content_overlay"):
            resolved_overlay = getattr(window, "content_overlay", None)
        if resolved_overlay is not None:
            self.set_overlay(resolved_overlay)

        self.connect("clicked", self._on_button_clicked)

    @property
    def popup_widget(self) -> Gtk.Box:
        return self._popup

    def set_overlay(self, overlay: Gtk.Overlay) -> None:
        if self._overlay is not None and self._popup.get_parent() is self._overlay:
            self._overlay.remove_overlay(self._popup)
        self._overlay = overlay
        if overlay is not None and self._popup.get_parent() is None:
            overlay.add_overlay(self._popup)
            overlay.set_measure_overlay(self._popup, False)

    def get_active(self) -> bool:
        return self._popup.get_visible()

    def update_state(self) -> None:
        """Hook for subclasses to refresh state before display."""
        pass

    def popup(self) -> None:
        self.update_state()

        if hasattr(self._window, "close_all_menus"):
            self._window.close_all_menus(except_menu=self)

        self._reposition()
        self._popup.set_visible(True)

    def popdown(self) -> None:
        if self._popup.get_visible():
            self._popup.set_visible(False)
        if hasattr(self, "_close_submenus") and callable(self._close_submenus):
            self._close_submenus()

    def _reposition(self) -> None:
        if self._overlay is None and hasattr(self._window, "content_overlay"):
            self.set_overlay(getattr(self._window, "content_overlay"))
        if self._overlay is not None and self.get_parent() is not None:
            ok, rect = self.compute_bounds(self._overlay)
            if ok:
                x = max(0, int(rect.get_x()))
                y = max(0, int(rect.get_y() + rect.get_height()))
                self._popup.set_margin_start(x)
                self._popup.set_margin_top(y)

    def _on_button_clicked(self, _button: Gtk.Button) -> None:
        if self.get_active():
            self.popdown()
        else:
            self.popup()
