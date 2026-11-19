from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from types import SimpleNamespace
from typing import TYPE_CHECKING

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gtk

from codevision.space.graph_data import GraphNodeData
from codevision.space.space_view import SpaceView

from .helpers import (
    analysis_panel_for,
    analysis_view_for,
    graph_node_for_context,
    space_view_for,
    text_from_widget,
)

if TYPE_CHECKING:
    from ..ui.analysis_panel import AnalysisPanel
    from ..ui.widgets.menu_context import MenuContext


@dataclass(frozen=True, slots=True)
class _Selection:
    key: tuple[str, str]
    node: GraphNodeData | None
    text: str | None
    highlight_widget: Gtk.Widget | None


def is_enabled(context: MenuContext) -> bool:
    panel = analysis_panel_for(context)
    return (
        context.kind == "analysis-panel"
        and panel is not None
        and panel.current_section not in {"Space", "Export"}
        and analysis_view_for(context) is not None
        and space_view_for(context) is not None
    )


def run(context: MenuContext) -> None:
    panel = analysis_panel_for(context)
    view = analysis_view_for(context)
    if panel is None or view is None or not is_enabled(context):
        return
    previous = getattr(panel, "_multi_select_session", None)
    if isinstance(previous, _MultiSelectSession):
        previous.cancel()
    session = _MultiSelectSession(panel, view, context.set_status)
    panel._multi_select_session = session
    session.start()


class _MultiSelectSession:
    def __init__(
        self,
        panel: AnalysisPanel,
        view: Gtk.Widget,
        set_status: Callable[[str], None] | None,
    ) -> None:
        self.panel = panel
        self.view = view
        self.set_status = set_status
        self.selected: dict[tuple[str, str], _Selection] = {}
        self.hovered: _Selection | None = None
        self._highlighted_widgets: dict[int, Gtk.Widget] = {}
        self._previous_all_nodes_selected = getattr(
            self.view, "_all_nodes_selected", None
        )

        self.motion = Gtk.EventControllerMotion.new()
        self.motion.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        self.motion.connect("motion", self._on_motion)
        self.motion.connect("leave", self._on_leave)
        self.view.add_controller(self.motion)

        self.click = Gtk.GestureClick.new()
        self.click.set_button(Gdk.BUTTON_PRIMARY)
        self.click.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        self.click.connect("pressed", self._on_pressed)
        self.view.add_controller(self.click)

        self.keys = Gtk.EventControllerKey.new()
        self.keys.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        self.keys.connect("key-pressed", self._on_key_pressed)
        self.panel.add_controller(self.keys)
        self._stack_handler = self.panel.views.connect(
            "notify::visible-child", self._on_view_changed
        )

    def start(self) -> None:
        if self._previous_all_nodes_selected is not None:
            setattr(self.view, "_all_nodes_selected", False)
            self._refresh_view()
        self.panel.set_focusable(True)
        self.panel.grab_focus()
        self._set_status(
            "Hover an item and click to select it. "
            "Press Enter to forward; Esc to cancel."
        )

    def _on_motion(
        self,
        _controller: Gtk.EventControllerMotion,
        x: float,
        y: float,
    ) -> None:
        self._set_hovered(self._selection_at(x, y))

    def _on_leave(self, _controller: Gtk.EventControllerMotion) -> None:
        self._set_hovered(None)

    def _on_view_changed(self, _stack: Gtk.Stack, _property: object) -> None:
        if self.panel.views.get_visible_child() is not self.view:
            self.cancel()

    def _on_pressed(
        self,
        gesture: Gtk.GestureClick,
        _press_count: int,
        x: float,
        y: float,
    ) -> None:
        selection = self._selection_at(x, y)
        if selection is None:
            return
        gesture.set_state(Gtk.EventSequenceState.CLAIMED)
        self._set_hovered(selection)
        if selection.key in self.selected:
            del self.selected[selection.key]
        else:
            self.selected[selection.key] = selection
        self._refresh_highlights()
        self._set_status(
            f"{len(self.selected)} item(s) selected. "
            "Press Enter to forward; Esc to cancel."
        )

    def _on_key_pressed(
        self,
        _controller: Gtk.EventControllerKey,
        keyval: int,
        _keycode: int,
        _state: Gdk.ModifierType,
    ) -> bool:
        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            self.finish()
            return True
        if keyval == Gdk.KEY_Escape:
            self.cancel()
            return True
        return False

    def _selection_at(self, x: float, y: float) -> _Selection | None:
        picked = self.view.pick(x, y, Gtk.PickFlags.DEFAULT)
        if picked is None:
            return None

        position: tuple[float, float] | None = None
        canvas = getattr(self.view, "canvas", None)
        if isinstance(canvas, Gtk.Widget) and self._is_within(picked, canvas):
            position = self.view.translate_coordinates(canvas, x, y)

        context = SimpleNamespace(
            widget=picked,
            kind="analysis-panel",
            analysis_panel=self.panel,
            analysis_position=position,
        )
        node = graph_node_for_context(context)
        if node is not None:
            on_canvas = isinstance(canvas, Gtk.Widget) and self._is_within(
                picked, canvas
            )
            widget = None if on_canvas else self._highlight_widget(picked)
            return _Selection(
                (self.panel.current_section, f"node:{node.node_id}"),
                node,
                None,
                widget,
            )

        text = text_from_widget(picked)
        if text is None:
            return None
        widget = self._highlight_widget(picked)
        return _Selection(
            (self.panel.current_section, f"widget:{id(widget)}"),
            None,
            text,
            widget,
        )

    def _set_hovered(self, selection: _Selection | None) -> None:
        if (
            self.hovered is not None
            and selection is not None
            and self.hovered.key == selection.key
        ):
            return
        self.hovered = selection
        self._refresh_highlights()

    def _refresh_highlights(self) -> None:
        desired: dict[int, tuple[Gtk.Widget, bool]] = {}
        for selection in self.selected.values():
            widget = selection.highlight_widget
            if widget is not None:
                desired[id(widget)] = (widget, True)
        if self.hovered is not None and self.hovered.highlight_widget is not None:
            widget = self.hovered.highlight_widget
            desired[id(widget)] = (
                widget,
                id(widget) in desired,
            )
        for key, widget in self._highlighted_widgets.items():
            if key not in desired:
                widget.remove_css_class("analysis-multi-select-selected")
                widget.remove_css_class("analysis-multi-select-hover")
        for key, (widget, selected) in desired.items():
            widget.remove_css_class("analysis-multi-select-hover")
            widget.remove_css_class("analysis-multi-select-selected")
            widget.add_css_class(
                "analysis-multi-select-selected"
                if selected
                else "analysis-multi-select-hover"
            )
        self._highlighted_widgets = {
            key: widget for key, (widget, _selected) in desired.items()
        }

        selected_ids = {
            item.node.node_id
            for item in self.selected.values()
            if item.node is not None
        }
        hovered_id = (
            self.hovered.node.node_id
            if self.hovered is not None and self.hovered.node is not None
            else None
        )
        setattr(self.view, "_multi_select_node_ids", selected_ids)
        setattr(self.view, "_multi_select_hover_node_id", hovered_id)
        self._refresh_view()

    def _refresh_view(self) -> None:
        update_ast_style = getattr(self.view, "_update_ast_selection_style", None)
        if callable(update_ast_style):
            update_ast_style()
        canvas = getattr(self.view, "canvas", None)
        if isinstance(canvas, Gtk.Widget):
            canvas.queue_draw()

    def finish(self) -> None:
        selections = tuple(self.selected.values())
        if not selections:
            self._set_status("Select one or more items before pressing Enter.")
            return
        self._cleanup()
        space = self.panel._section_placeholders.get("Space")
        if not isinstance(space, SpaceView):
            raise RuntimeError("The Space board is unavailable.")
        self.panel.select_section("Space")
        forwarded = 0
        for selection in selections:
            if selection.node is not None:
                space.add_graph_node(selection.node)
                forwarded += 1
            elif selection.text:
                space.add_text_box(selection.text)
                forwarded += 1
        self._set_status(f"Forwarded {forwarded} item(s) to Space.")

    def cancel(self) -> None:
        self._cleanup()
        self._set_status("Multiple selection cancelled.")

    def _cleanup(self) -> None:
        self.view.remove_controller(self.motion)
        self.view.remove_controller(self.click)
        self.panel.remove_controller(self.keys)
        self.panel.views.disconnect(self._stack_handler)
        for widget in self._highlighted_widgets.values():
            widget.remove_css_class("analysis-multi-select-selected")
            widget.remove_css_class("analysis-multi-select-hover")
        self._highlighted_widgets.clear()
        setattr(self.view, "_multi_select_node_ids", set())
        setattr(self.view, "_multi_select_hover_node_id", None)
        if self._previous_all_nodes_selected is not None:
            setattr(
                self.view,
                "_all_nodes_selected",
                self._previous_all_nodes_selected,
            )
        self._refresh_view()
        if getattr(self.panel, "_multi_select_session", None) is self:
            delattr(self.panel, "_multi_select_session")

    @staticmethod
    def _highlight_widget(widget: Gtk.Widget) -> Gtk.Widget:
        current: Gtk.Widget | None = widget
        while current is not None:
            if isinstance(
                current,
                (
                    Gtk.Button,
                    Gtk.Entry,
                    Gtk.Label,
                    Gtk.ListBoxRow,
                    Gtk.TextView,
                    Gtk.TreeExpander,
                ),
            ):
                return current
            current = current.get_parent()
        return widget

    @staticmethod
    def _is_within(widget: Gtk.Widget, ancestor: Gtk.Widget) -> bool:
        current: Gtk.Widget | None = widget
        while current is not None:
            if current is ancestor:
                return True
            current = current.get_parent()
        return False

    def _set_status(self, message: str) -> None:
        if self.set_status is not None:
            self.set_status(message)
