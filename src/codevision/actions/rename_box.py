from __future__ import annotations

from typing import TYPE_CHECKING

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from .helpers import analysis_panel_for, space_item_for, space_view_for
from space.graph_item import GraphNodeItem
from space.import_item import ImportItem
from space.textbox import TextBox

if TYPE_CHECKING:
    from ..ui.widgets.menu_context import MenuContext


def is_enabled(context: MenuContext) -> bool:
    panel = analysis_panel_for(context)
    return (
        context.kind == "analysis-panel"
        and panel is not None
        and panel.current_section == "Space"
        and space_view_for(context) is not None
        and space_item_for(context) is not None
    )


def run(context: MenuContext) -> None:
    item = space_item_for(context)
    if item is None:
        return
    root = context.widget.get_root()
    if not isinstance(root, Gtk.Window):
        raise RuntimeError("The box rename dialog cannot be opened.")

    current_name = (
        item.title
        if isinstance(item, (TextBox, GraphNodeItem))
        else item.display_name
    )
    dialog = Gtk.Dialog(
        title="Rename Box",
        transient_for=root,
        modal=True,
    )
    dialog.add_button("_Cancel", Gtk.ResponseType.CANCEL)
    dialog.add_button("_Rename", Gtk.ResponseType.ACCEPT)
    dialog.set_default_response(Gtk.ResponseType.ACCEPT)
    content = dialog.get_content_area()
    content.set_spacing(8)
    content.set_margin_top(12)
    content.set_margin_bottom(12)
    content.set_margin_start(12)
    content.set_margin_end(12)
    entry = Gtk.Entry()
    entry.set_text(current_name)
    entry.set_activates_default(True)
    content.append(entry)

    def on_response(_dialog: Gtk.Dialog, response: int) -> None:
        if response == Gtk.ResponseType.ACCEPT:
            name = entry.get_text().strip()
            if name:
                if isinstance(item, TextBox):
                    item.set_title(name)
                elif isinstance(item, GraphNodeItem):
                    item.set_title(name)
                elif isinstance(item, ImportItem):
                    item.set_display_name(name)
            elif context.set_status is not None:
                context.set_status("Box name cannot be empty.")
        dialog.destroy()

    dialog.connect("response", on_response)
    dialog.present()
    entry.grab_focus()
    entry.select_region(0, -1)
