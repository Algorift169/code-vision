from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from ..services.save import SaveService
from .editor import EditorPanel


class EditorTabs(Gtk.Notebook):
    """Notebook whose pages are editor instances for opened files."""

    def __init__(
        self,
        on_active_changed: Callable[[EditorPanel | None], None] | None = None,
    ) -> None:
        super().__init__()
        self.set_name("editor-tabs")
        self.set_scrollable(True)
        self.set_show_border(False)
        self.set_show_tabs(False)
        self._on_active_changed = on_active_changed
        self._tab_labels: dict[int, Gtk.Label] = {}
        self.connect("switch-page", self._on_switch_page)

    @property
    def active_editor(self) -> EditorPanel | None:
        page = self.get_nth_page(self.get_current_page())
        return page if isinstance(page, EditorPanel) else None

    def open_file(self, path: Path) -> EditorPanel:
        """Open a file in its own editor tab, selecting it if already open."""
        resolved_path = path.expanduser().resolve()
        for page_number in range(self.get_n_pages()):
            page = self.get_nth_page(page_number)
            if isinstance(page, EditorPanel) and page.file_path == resolved_path:
                self.set_current_page(page_number)
                return page

        editor = EditorPanel()
        editor.set_name("editor-panel")
        editor.open_file(resolved_path)

        tab_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        tab_label = Gtk.Label(label=resolved_path.name)
        tab_label.add_css_class("editor-tab-label")
        tab_header.append(tab_label)

        close_button = Gtk.Button()
        close_button.set_child(Gtk.Image.new_from_icon_name("window-close-symbolic"))
        close_button.set_tooltip_text(f"Close {resolved_path.name}")
        close_button.add_css_class("editor-tab-close")
        close_button.connect("clicked", lambda *_args: self.close_editor(editor))
        tab_header.append(close_button)

        page_number = self.append_page(editor, tab_header)
        self._tab_labels[id(editor)] = tab_label
        self.set_tab_reorderable(editor, True)
        self.set_show_tabs(True)
        self.set_current_page(page_number)
        self._notify_active_changed()
        return editor

    def save_active(
        self, save_service: SaveService, path: Path | None = None
    ) -> Path:
        editor = self.active_editor
        if editor is None:
            raise ValueError("There is no active editor tab")

        saved_path = editor.save_file(save_service, path)
        tab_label = self._tab_labels.get(id(editor))
        if tab_label is not None:
            tab_label.set_text(saved_path.name)
        return saved_path

    def close_editor(self, editor: EditorPanel) -> None:
        page_number = self.page_num(editor)
        if page_number < 0:
            return

        self.remove_page(page_number)
        self._tab_labels.pop(id(editor), None)
        if self.get_n_pages() == 0:
            self.set_show_tabs(False)
        self._notify_active_changed()

    def _on_switch_page(
        self, _notebook: Gtk.Notebook, _page: Gtk.Widget, _page_number: int
    ) -> None:
        self._notify_active_changed()

    def _notify_active_changed(self) -> None:
        if self._on_active_changed is not None:
            self._on_active_changed(self.active_editor)
