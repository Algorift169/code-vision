from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk


class EditMenuButton(Gtk.MenuButton):
    """GTK 4 Edit menu that delegates to the active editor and window actions."""

    def __init__(self, window: object) -> None:
        super().__init__()
        self._window = window
        self.set_label("Edit")
        self.add_css_class("menu-button")

        self._popover = self._create_popover()
        self._content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        self._content.add_css_class("context-menu-content")
        self._popover.set_child(self._content)
        self.set_popover(self._popover)
        self.connect("notify::active", self._on_menu_active_changed)
        self._items: dict[str, Gtk.Button] = {}
        self._build_items()

    def _create_popover(self) -> Gtk.Popover:
        popover = Gtk.Popover()
        popover.set_name("codevision-context-menu")
        popover.set_has_arrow(False)
        popover.set_autohide(True)
        popover.add_css_class("codevision-context-menu")
        return popover

    def _build_items(self) -> None:
        self._items["undo"] = self._append_action("Undo", "Ctrl+Z", self._window.undo)
        self._items["redo"] = self._append_action("Redo", "Ctrl+Y", self._window.redo)
        self._content.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        self._items["cut"] = self._append_action("Cut", "Ctrl+X", self._window.cut)
        self._items["copy"] = self._append_action("Copy", "Ctrl+C", self._window.copy)
        self._items["paste"] = self._append_action("Paste", "Ctrl+V", self._window.paste)
        self._content.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        self._items["find"] = self._append_action("Find", "Ctrl+F", self._window.find)
        self._items["replace"] = self._append_action(
            "Replace", "Ctrl+H", self._window.replace
        )
        self._content.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        self._items["find-in-files"] = self._append_action(
            "Find in Files", "Ctrl+Shift+F", self._window.find_in_files
        )
        self._items["replace-in-files"] = self._append_action(
            "Replace in Files", "Ctrl+Shift+H", self._window.replace_in_files
        )
        self._content.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        self._items["toggle-line-comment"] = self._append_action(
            "Toggle Line Comment", "Ctrl+/", self._window.toggle_line_comment
        )
        self._items["toggle-block-comment"] = self._append_action(
            "Toggle Block Comment", "Ctrl+Shift+A", self._window.toggle_block_comment
        )
        self._items["expand-abbreviation"] = self._append_action(
            "Emmet: Expand Abbreviation", "Tab", self._window.expand_abbreviation
        )

    def _append_action(
        self, label: str, shortcut: str, callback: Callable[[], None]
    ) -> Gtk.Button:
        button = self._make_button(label, shortcut, callback)
        self._content.append(button)
        return button

    def _make_button(
        self, label: str, shortcut: str, callback: Callable[[], None]
    ) -> Gtk.Button:
        button = Gtk.Button()
        button.set_has_frame(False)
        button.set_halign(Gtk.Align.FILL)
        button.add_css_class("context-menu-item")
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        row.set_hexpand(True)
        title = Gtk.Label(label=label)
        title.set_halign(Gtk.Align.START)
        title.set_hexpand(True)
        title.set_xalign(0)
        shortcut_label = Gtk.Label(label=shortcut)
        shortcut_label.set_halign(Gtk.Align.END)
        shortcut_label.add_css_class("muted-label")
        row.append(title)
        row.append(shortcut_label)
        button.set_child(row)
        button.connect("clicked", lambda _button: (self.popdown(), callback()))
        return button

    def _on_menu_active_changed(self, *_args: object) -> None:
        if self.get_active():
            self.update_state()

    def update_state(self) -> None:
        editor = getattr(self._window, "editor_tabs", None)
        active = editor.active_editor if editor is not None else None
        has_editor = active is not None

        items = [
            "undo",
            "redo",
            "cut",
            "copy",
            "paste",
            "find",
            "replace",
            "find-in-files",
            "replace-in-files",
            "toggle-line-comment",
            "toggle-block-comment",
            "expand-abbreviation",
        ]
        for item_name in items:
            self._items[item_name].set_sensitive(has_editor)

        if not has_editor:
            return

        buffer = active.buffer
        can_undo = bool(getattr(buffer, "get_can_undo", lambda: False)())
        can_redo = bool(getattr(buffer, "get_can_redo", lambda: False)())
        selection = getattr(buffer, "get_selection_bounds", lambda: ())()
        has_selection = bool(selection) and not selection[0].equal(selection[1])
        view = getattr(active, "source_view", None)
        editable = bool(view.get_editable()) if view is not None else True

        self._items["undo"].set_sensitive(can_undo)
        self._items["redo"].set_sensitive(can_redo)
        self._items["cut"].set_sensitive(has_selection and editable)
        self._items["copy"].set_sensitive(has_selection)
        self._items["paste"].set_sensitive(editable)
        self._items["find"].set_sensitive(True)
        self._items["replace"].set_sensitive(True)
        self._items["find-in-files"].set_sensitive(True)
        self._items["replace-in-files"].set_sensitive(True)
        self._items["toggle-line-comment"].set_sensitive(editable)
        self._items["toggle-block-comment"].set_sensitive(editable)
        self._items["expand-abbreviation"].set_sensitive(editable)
