from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from ....services.file_operations import FileOperationService
from ..menu_context import MenuContext

_SERVICE = FileOperationService()


def is_enabled(context: MenuContext) -> bool:
    return _is_project_item(context)


def _is_project_item(context: MenuContext) -> bool:
    if context.kind != "explorer" or context.path is None or context.project_root is None:
        return False
    try:
        path = context.path.resolve()
        root = context.project_root.resolve()
        path.relative_to(root)
    except (OSError, ValueError):
        return False
    return path != root


def run(context: MenuContext) -> None:
    if not is_enabled(context) or context.path is None:
        return

    root = context.widget.get_root()
    parent = root if isinstance(root, Gtk.Window) else None
    dialog = Gtk.Dialog(title="Rename", transient_for=parent, modal=True)
    dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
    dialog.add_button("Rename", Gtk.ResponseType.ACCEPT)
    dialog.set_default_response(Gtk.ResponseType.ACCEPT)

    content = dialog.get_content_area()
    content.set_spacing(8)
    content.set_margin_top(12)
    content.set_margin_bottom(12)
    content.set_margin_start(12)
    content.set_margin_end(12)
    entry = Gtk.Entry()
    entry.set_text(context.path.name)
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
            renamed_path = _SERVICE.rename(context.path, entry.get_text())
        except (OSError, ValueError) as error:
            error_label.set_text(str(error))
            error_label.set_visible(True)
            return

        dialog.close()
        if context.on_path_renamed is not None:
            context.on_path_renamed(context.path, renamed_path)

    dialog.connect("response", on_response)
    dialog.present()
    entry.grab_focus()
    entry.select_region(0, -1)