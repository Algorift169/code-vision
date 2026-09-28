from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from ...services.new_file import NewFileService


class NewFileAction(Gtk.Button):
    """Project Explorer button that creates and opens a new file."""

    def __init__(
        self,
        parent: Gtk.Widget,
        get_directory: Callable[[], Path],
        on_created: Callable[[Path], None],
    ) -> None:
        super().__init__()
        self._parent = parent
        self._get_directory = get_directory
        self._on_created = on_created
        self._service = NewFileService()

        self.set_child(Gtk.Image.new_from_icon_name("document-new-symbolic"))
        self.set_tooltip_text("New File")
        self.add_css_class("explorer-action")
        self.connect("clicked", lambda *_args: self.activate())

    def activate(self) -> None:
        self.activate_in(self._get_directory())

    def activate_in(self, directory: Path) -> None:
        self._show_create_dialog(directory)

    def _show_create_dialog(self, directory: Path) -> None:
        root = self._parent.get_root()
        parent_window = root if isinstance(root, Gtk.Window) else None
        dialog = Gtk.Dialog(title="New File", transient_for=parent_window, modal=True)
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("Create", Gtk.ResponseType.ACCEPT)

        content = dialog.get_content_area()
        content.set_spacing(8)
        content.set_margin_top(12)
        content.set_margin_bottom(12)
        content.set_margin_start(12)
        content.set_margin_end(12)

        entry = Gtk.Entry()
        entry.set_placeholder_text("File name")
        entry.set_activates_default(True)
        content.append(entry)

        error_label = Gtk.Label()
        error_label.set_halign(Gtk.Align.START)
        error_label.add_css_class("explorer-error")
        error_label.set_visible(False)
        content.append(error_label)

        def on_response(_dialog: Gtk.Dialog, response: int) -> None:
            if response != Gtk.ResponseType.ACCEPT:
                dialog.close()
                return

            try:
                path = self._service.create(directory, entry.get_text())
            except (OSError, ValueError) as error:
                error_label.set_text(str(error))
                error_label.set_visible(True)
                return

            dialog.close()
            self._on_created(path)

        dialog.connect("response", on_response)
        dialog.present()
        entry.grab_focus()