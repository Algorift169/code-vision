from __future__ import annotations

from typing import TYPE_CHECKING

import gi

gi.require_version("Gdk", "4.0")
from gi.repository import Gdk

from .helpers import space_item_for, text_from_widget
from codevision.space.import_item import ImportItem

if TYPE_CHECKING:
    from ..ui.widgets.menu_context import MenuContext


def is_enabled(context: MenuContext) -> bool:
    return context.kind == "analysis-panel" and (
        space_item_for(context) is not None or text_from_widget(context.widget) is not None
    )


def run(context: MenuContext) -> None:
    item = space_item_for(context)
    display = Gdk.Display.get_default()
    if display is None:
        raise RuntimeError("The system clipboard is unavailable.")
    clipboard = display.get_clipboard()
    if isinstance(item, ImportItem):
        from ..ui.widgets.menu_actions.copy import file_list_provider

        clipboard.set_content(file_list_provider((item.path,)))
        return
    text = text_from_widget(context.widget)
    if text is not None:
        clipboard.set_text(text)
