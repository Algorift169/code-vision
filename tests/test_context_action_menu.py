from pathlib import Path

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gtk

from codevision.ui.widgets.context_action_menu import ContextActionMenu
from codevision.ui.widgets.menu import ContextMenu
from codevision.ui.widgets.menu_context import MenuContext
from codevision.ui.widgets.menu_actions import delete, new_file, rename
from codevision.ui.explorer_actions.new_file import NewFileAction


class StatusLabel:
    def __init__(self) -> None:
        self.text = ""

    def set_text(self, text: str) -> None:
        self.text = text


class ActionWindow:
    def __init__(self) -> None:
        self.status_label = StatusLabel()


def test_context_actions_open_inline_forms(tmp_path: Path) -> None:
    target = tmp_path / "rename-me.txt"
    target.touch()
    overlay = Gtk.Overlay()
    anchor = Gtk.Button(label="Action")
    overlay.set_child(anchor)
    window = ActionWindow()
    menu = ContextActionMenu(window, overlay)
    created: list[Path] = []
    renamed: list[tuple[Path, Path]] = []
    deleted: list[Path] = []
    context = MenuContext(
        widget=anchor,
        kind="explorer",
        path=target,
        project_root=tmp_path,
        open_action_menu=menu.popup_for,
        on_path_created=created.append,
        on_path_renamed=lambda old, new: renamed.append((old, new)),
        on_path_deleted=deleted.append,
        set_status=window.status_label.set_text,
    )

    assert new_file.is_enabled(context)
    assert rename.is_enabled(context)
    assert delete.is_enabled(context)

    menu.popup_for("new-file", context, anchor)
    menu._entry.set_text("created.txt")
    menu._on_confirm()
    created_path = tmp_path / "created.txt"
    assert created == [created_path]
    assert created_path.is_file()
    assert window.status_label.text == ""
    assert not menu.get_visible()

    menu.popup_for("rename", context, anchor)
    menu._entry.set_text("renamed.txt")
    menu._on_confirm()
    renamed_path = tmp_path / "renamed.txt"
    assert renamed == [(target, renamed_path)]
    assert renamed_path.is_file()
    assert not target.exists()

    context.path = renamed_path
    menu.popup_for("delete", context, anchor)
    menu._on_confirm()
    assert deleted == [renamed_path]
    assert not renamed_path.exists()
    assert not menu.get_visible()


def test_context_action_errors_stay_in_the_inline_form(tmp_path: Path) -> None:
    overlay = Gtk.Overlay()
    anchor = Gtk.Button(label="Action")
    overlay.set_child(anchor)
    menu = ContextActionMenu(ActionWindow(), overlay)
    context = MenuContext(
        widget=anchor,
        kind="window",
        project_root=tmp_path,
        open_action_menu=menu.popup_for,
    )

    menu.popup_for("new-file", context, anchor)
    menu._entry.set_text("../outside.txt")
    menu._on_confirm()

    assert menu.get_visible()
    assert menu._error_label.get_visible()
    assert menu._error_label.get_text()
    assert not (tmp_path.parent / "outside.txt").exists()


def test_context_action_menu_closes_on_escape() -> None:
    overlay = Gtk.Overlay()
    anchor = Gtk.Button(label="Action")
    overlay.set_child(anchor)
    menu = ContextActionMenu(ActionWindow(), overlay)
    context = MenuContext(widget=anchor, kind="window")
    menu.popup_for("new-file", context, anchor)

    assert menu._on_key_pressed(
        None, Gdk.KEY_Escape, 0, Gdk.ModifierType(0)
    )
    assert not menu.get_visible()


def test_context_menu_dispatches_inline_action_with_clicked_anchor() -> None:
    overlay = Gtk.Overlay()
    content = Gtk.Box()
    overlay.set_child(content)
    opened: list[tuple[str, MenuContext, Gtk.Widget]] = []
    context = MenuContext(
        widget=content,
        kind="window",
        open_action_menu=lambda action, ctx, anchor: opened.append(
            (action, ctx, anchor)
        ),
    )
    menu = ContextMenu(overlay, content, lambda _x, _y: context)
    menu._context = context
    button = menu._items["new-file"][0]

    menu._on_action_clicked(button, "new-file")

    assert opened == [("new-file", context, button)]
    assert context.action_anchor is button
    assert not menu.get_visible()


def test_explorer_new_file_button_opens_inline_form(tmp_path: Path) -> None:
    directory = tmp_path / "project"
    directory.mkdir()
    created: list[Path] = []
    opened: list[tuple[str, MenuContext, Gtk.Widget]] = []
    action = NewFileAction(lambda: directory, created.append)
    action.set_action_menu(
        lambda action_id, context, anchor: opened.append(
            (action_id, context, anchor)
        )
    )

    action.activate()

    assert action.get_sensitive()
    assert len(opened) == 1
    action_id, context, anchor = opened[0]
    assert action_id == "new-file"
    assert context.directory == directory
    assert context.on_path_created == created.append
    assert anchor is action
