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
    dialog = Gtk.Dialog(title="Delete", transient_for=parent, modal=True)
    dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
    dialog.add_button("Delete", Gtk.ResponseType.ACCEPT)
    dialog.set_default_response(Gtk.ResponseType.CANCEL)

    label = Gtk.Label(label=f"Delete '{context.path.name}'? This cannot be undone.")
    label.set_wrap(True)
    label.set_margin_top(12)
    label.set_margin_bottom(12)
    label.set_margin_start(12)
    label.set_margin_end(12)
    dialog.get_content_area().append(label)

    def on_response(_dialog: Gtk.Dialog, response: int) -> None:
        if response == Gtk.ResponseType.ACCEPT:
            try:
                _SERVICE.delete(context.path)
                if context.on_path_deleted is not None:
                    context.on_path_deleted(context.path)
            except OSError as error:
                if context.set_status is not None:
                    context.set_status(str(error))
        dialog.close()

    dialog.connect("response", on_response)
    dialog.present()