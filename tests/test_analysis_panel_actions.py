import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from codevision.app.main_window import CodeVisionWindow
from codevision.actions.action import ANALYSIS_PANEL_ACTIONS
from codevision.ui.widgets.menu import ContextMenu
from codevision.ui.widgets.menu_context import MenuContext


def test_right_click_context_shows_analysis_panel_actions_only() -> None:
    overlay = Gtk.Overlay()
    content = Gtk.Box()
    overlay.set_child(content)
    menu = ContextMenu(
        overlay,
        content,
        lambda _x, _y: MenuContext(
            widget=content,
            kind="analysis-panel",
        ),
    )

    menu._on_pressed(None, 1, 42.0, 68.0)

    visible_actions = [
        action_id
        for action_id, (button, _action) in menu._items.items()
        if button.get_visible()
    ]
    assert visible_actions == [
        action_id
        for action_id, _label, _icon, _action in ANALYSIS_PANEL_ACTIONS
    ]
    assert menu.get_visible()


def test_analysis_panel_actions_are_scoped_to_analysis_context() -> None:
    panel_context = MenuContext(widget=Gtk.Box(), kind="analysis-panel")
    window_context = MenuContext(widget=Gtk.Box(), kind="window")

    for _action_id, _label, _icon, action in ANALYSIS_PANEL_ACTIONS:
        assert action.is_enabled(panel_context)
        assert not action.is_enabled(window_context)


def test_main_window_classifies_panel_descendant_as_analysis_context() -> None:
    analysis_panel = Gtk.Box()
    target = Gtk.Label(label="analysis content")
    analysis_panel.append(target)

    class ContextRoot:
        def pick(self, _x: float, _y: float, _flags: Gtk.PickFlags) -> Gtk.Widget:
            return target

    class DummyWindow:
        _is_within = staticmethod(CodeVisionWindow._is_within)

        def __init__(self) -> None:
            self._context_menu_root = ContextRoot()
            self.analysis_panel = analysis_panel

        def _generic_menu_context(self, widget: Gtk.Widget) -> MenuContext:
            return MenuContext(widget=widget, kind="window")

    context = CodeVisionWindow._window_menu_context_at(
        DummyWindow(), 0.0, 0.0
    )

    assert context.kind == "analysis-panel"
    assert context.widget is target
