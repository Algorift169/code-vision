from __future__ import annotations

import math
from pathlib import Path

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gio", "2.0")
gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gio, GLib, Gtk

from .color import Color, ColorPalette, DrawingColor
from .eraser import Eraser
from .import_item import ImportItem
from .importer import ImportedFile, describe_file
from .pen import Pen
from .rendo import Redo
from .textbox import TextBox
from .undo import Undo
from .zoom import SpaceZoom


_SPACE_TOOLS = (
    ("Pen", "Draw freehand"),
    ("Undo", "Undo the last board action"),
    ("Redo", "Redo the last undone board action"),
    ("Eraser", "Erase small portions of strokes"),
    ("Color", "Choose a drawing color"),
    ("Text Box", "Add a text box"),
    ("Import", "Import content"),
    ("Shapes", "Choose a shape"),
    ("Zoom In", "Zoom in"),
    ("Zoom Out", "Zoom out"),
    ("Export", "Export board content"),
)


class SpaceView(Gtk.Box):
    """Workspace shell for the Analysis Panel's Space board."""

    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.set_name("space-view")
        self.set_hexpand(True)
        self.set_vexpand(True)
        self.set_margin_start(4)
        self.set_margin_end(4)
        self.set_margin_top(4)
        self.set_margin_bottom(4)
        self.drawing_color = DrawingColor()
        self.color_preview: Gtk.DrawingArea | None = None
        self.text_boxes: list[TextBox] = []
        self.import_items: list[ImportItem] = []
        self._active_text_box: TextBox | None = None
        self._highlighted_text_box: TextBox | None = None
        self._import_dialog: Gtk.FileChooserDialog | None = None
        self._dragged_import_item: ImportItem | None = None
        self._import_drag_origin = (0.0, 0.0)
        self.zoom = SpaceZoom(self._apply_space_zoom)

        self.toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        self.toolbar.add_css_class("space-toolbar")

        self.tool_buttons: dict[str, Gtk.Widget] = {}
        for label, tooltip in _SPACE_TOOLS:
            if label in ("Pen", "Eraser", "Text Box"):
                button = Gtk.ToggleButton(label=label)
            elif label == "Color":
                button = Gtk.MenuButton()
                button.set_tooltip_text(tooltip)
                button.set_child(self._build_color_button_content())
                button.set_popover(ColorPalette(self.drawing_color))
            else:
                button = Gtk.Button(label=label)
            button.set_tooltip_text(tooltip)
            button.add_css_class("theme-toolbar-button")
            button.add_css_class("space-tool-button")
            self.toolbar.append(button)
            self.tool_buttons[label] = button
        for label, button in self.tool_buttons.items():
            if label == "Color":
                button.connect("notify::active", self._on_color_menu_active)
            elif label == "Import":
                button.connect("clicked", self._on_import_clicked)
            else:
                button.connect("clicked", self._on_toolbar_button_clicked)
        self.drawing_color.subscribe(self._on_drawing_color_changed)

        self.toolbar_scroller = Gtk.ScrolledWindow()
        self.toolbar_scroller.set_policy(
            Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER
        )
        self.toolbar_scroller.set_hexpand(True)
        self.toolbar_scroller.set_child(self.toolbar)
        self.append(self.toolbar_scroller)

        self.import_status = Gtk.Label()
        self.import_status.set_xalign(0)
        self.import_status.set_wrap(True)
        self.import_status.add_css_class("space-import-status")
        self.import_status.set_visible(False)
        self.append(self.import_status)

        self.canvas_scroller = Gtk.ScrolledWindow()
        self.canvas_scroller.set_policy(
            Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC
        )
        self.canvas_scroller.set_hexpand(True)
        self.canvas_scroller.set_vexpand(True)

        self.canvas = Gtk.DrawingArea()
        self.canvas.set_name("space-canvas")
        self.canvas.set_hexpand(True)
        self.canvas.set_vexpand(True)
        self.canvas.add_css_class("space-canvas")
        self.board = Gtk.Fixed()
        self.board.set_hexpand(True)
        self.board.set_vexpand(True)
        self.board.set_focusable(True)
        self.board.put(self.canvas, 0, 0)
        import_drag = Gtk.GestureDrag.new()
        import_drag.set_button(Gdk.BUTTON_PRIMARY)
        import_drag.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        import_drag.connect("drag-begin", self._on_import_drag_begin)
        import_drag.connect("drag-update", self._on_import_drag_update)
        import_drag.connect("drag-end", self._on_import_drag_end)
        self.board.add_controller(import_drag)
        file_drop = Gtk.DropTarget.new(Gdk.FileList.__gtype__, Gdk.DragAction.COPY)
        file_drop.connect("drop", self._on_files_dropped)
        self.board.add_controller(file_drop)
        self._canvas_width = 0
        self._canvas_height = 0
        self._extending_canvas = False
        self.pen = Pen(
            self.canvas,
            self._update_history_buttons,
            self.drawing_color,
            self.zoom,
        )
        self.eraser = Eraser(self.pen, self.zoom)
        self.undo_action = Undo(self.pen)
        self.redo_action = Redo(self.pen)
        self.tool_buttons["Undo"].connect(
            "clicked", lambda _button: self.undo_action.execute()
        )
        self.tool_buttons["Redo"].connect(
            "clicked", lambda _button: self.redo_action.execute()
        )
        self.tool_buttons["Zoom In"].connect(
            "clicked", lambda _button: self.zoom_in()
        )
        self.tool_buttons["Zoom Out"].connect(
            "clicked", lambda _button: self.zoom_out()
        )
        pen_button = self.tool_buttons["Pen"]
        pen_button.connect("toggled", self._on_pen_toggled)
        eraser_button = self.tool_buttons["Eraser"]
        eraser_button.connect("toggled", self._on_eraser_toggled)
        text_box_button = self.tool_buttons["Text Box"]
        text_box_button.connect("toggled", self._on_text_box_toggled)
        create_text_box = Gtk.GestureClick.new()
        create_text_box.set_button(Gdk.BUTTON_PRIMARY)
        create_text_box.connect("pressed", self._on_canvas_pressed)
        self.canvas.add_controller(create_text_box)
        self._update_history_buttons()
        self.canvas_scroller.set_child(self.board)
        self.append(self.canvas_scroller)

        self.canvas_scroller.connect("map", self._initialize_scrollable_canvas)

    def _on_pen_toggled(self, button: Gtk.ToggleButton) -> None:
        if button.get_active() and self.tool_buttons["Eraser"].get_active():
            self.tool_buttons["Eraser"].set_active(False)
        if button.get_active() and self.tool_buttons["Text Box"].get_active():
            self.tool_buttons["Text Box"].set_active(False)
        self.pen.set_enabled(button.get_active())

    def zoom_in(self) -> None:
        self.zoom.zoom_in()

    def zoom_out(self) -> None:
        self.zoom.zoom_out()

    def _apply_space_zoom(self) -> None:
        self._extending_canvas = True
        self.canvas.set_content_width(self.zoom.to_pixels(self._canvas_width))
        self.canvas.set_content_height(self.zoom.to_pixels(self._canvas_height))
        self.board.set_size_request(
            self.zoom.to_pixels(self._canvas_width),
            self.zoom.to_pixels(self._canvas_height),
        )
        for text_box in self.text_boxes:
            text_box.apply_zoom()
        for item in self.import_items:
            item.apply_zoom()
        self._extending_canvas = False
        self.canvas.queue_draw()

    def _on_import_clicked(self, _button: Gtk.Button) -> None:
        self._clear_text_box_highlight()
        root = self.get_root()
        if not isinstance(root, Gtk.Window):
            self._show_import_status("Open Space in a window to import files.")
            return
        dialog = Gtk.FileChooserDialog(
            title="Import files to Space",
            transient_for=root,
            action=Gtk.FileChooserAction.OPEN,
            modal=True,
        )
        dialog.add_button("_Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("_Import", Gtk.ResponseType.ACCEPT)
        dialog.set_default_response(Gtk.ResponseType.ACCEPT)
        dialog.add_css_class("space-file-chooser")
        dialog.set_select_multiple(True)
        dialog.connect("response", self._on_import_response)
        self._import_dialog = dialog
        dialog.present()

    def _on_import_response(
        self, dialog: Gtk.FileChooserDialog, response: int
    ) -> None:
        if response == Gtk.ResponseType.ACCEPT:
            files = dialog.get_files()
            paths = [
                files.get_item(index).get_path()
                for index in range(files.get_n_items())
            ]
            has_non_local_files = any(path is None for path in paths)
            self.import_files([Path(path) for path in paths if path is not None])
            if has_non_local_files:
                self._show_import_status("Only local files can be imported.")
        dialog.destroy()
        self._import_dialog = None

    def _on_files_dropped(
        self,
        _target: Gtk.DropTarget,
        value: Gdk.FileList,
        x: float,
        y: float,
    ) -> bool:
        files = value.get_files()
        paths = [file.get_path() for file in files]
        has_non_local_files = any(path is None for path in paths)
        local_paths = [Path(path) for path in paths if path is not None]
        if not local_paths:
            if has_non_local_files:
                self._show_import_status("Only local files can be imported.")
            return False
        added = self.import_files(local_paths, self.zoom.to_board(x, y))
        if has_non_local_files:
            self._show_import_status("Only local files can be imported.")
        return bool(added)

    def import_files(
        self,
        paths: list[Path],
        position: tuple[float, float] | None = None,
    ) -> list[ImportItem]:
        added: list[ImportItem] = []
        errors: list[str] = []
        origin_x, origin_y = position or (
            24.0 + (len(self.import_items) % 4) * 24.0,
            24.0 + (len(self.import_items) // 4) * 24.0,
        )
        for index, path in enumerate(paths):
            try:
                details = describe_file(path)
                item_position = (
                    max(0.0, origin_x + (index % 4) * 24.0),
                    max(0.0, origin_y + (index // 4) * 24.0),
                )
                item = self._create_import_item(details, item_position)
            except (OSError, ValueError, GLib.Error) as error:
                errors.append(str(error))
                continue
            added.append(item)

        if errors:
            self._show_import_status("; ".join(errors))
        elif added:
            self.import_status.set_visible(False)
        return added

    def _create_import_item(
        self,
        details: ImportedFile,
        position: tuple[float, float],
    ) -> ImportItem:
        item = ImportItem(
            details.path,
            details.content_type,
            details.mime_type,
            self.zoom,
            position,
        )
        self.board.put(
            item,
            item.x * self.zoom.scale,
            item.y * self.zoom.scale,
        )
        self.import_items.append(item)
        self._ensure_import_extent(item)
        return item

    def _show_import_status(self, message: str) -> None:
        self.import_status.set_text(message)
        self.import_status.set_visible(True)

    def _on_import_drag_begin(
        self, gesture: Gtk.GestureDrag, x: float, y: float
    ) -> None:
        picked = self.board.pick(x, y, Gtk.PickFlags.DEFAULT)
        while picked is not None and not isinstance(picked, ImportItem):
            picked = picked.get_parent()
        if not isinstance(picked, ImportItem):
            self._dragged_import_item = None
            gesture.set_state(Gtk.EventSequenceState.DENIED)
            return
        self._dragged_import_item = picked
        self._import_drag_origin = (picked.x, picked.y)
        gesture.set_state(Gtk.EventSequenceState.CLAIMED)
        self._clear_text_box_highlight()
        self.board.grab_focus()

    def _on_import_drag_update(
        self,
        _gesture: Gtk.GestureDrag,
        offset_x: float,
        offset_y: float,
    ) -> None:
        item = self._dragged_import_item
        if item is None:
            return
        item.x = max(
            0.0, self._import_drag_origin[0] + offset_x / self.zoom.scale
        )
        item.y = max(
            0.0, self._import_drag_origin[1] + offset_y / self.zoom.scale
        )
        self.board.move(
            item,
            item.x * self.zoom.scale,
            item.y * self.zoom.scale,
        )
        self._ensure_import_extent(item)

    def _on_import_drag_end(
        self,
        _gesture: Gtk.GestureDrag,
        _offset_x: float,
        _offset_y: float,
    ) -> None:
        self._dragged_import_item = None

    def _ensure_import_extent(self, item: ImportItem) -> None:
        right = math.ceil(item.x + item.WIDTH)
        bottom = math.ceil(item.y + item.HEIGHT)
        if right > self._canvas_width:
            self._set_canvas_extent("width", right)
        if bottom > self._canvas_height:
            self._set_canvas_extent("height", bottom)

    def _build_color_button_content(self) -> Gtk.Box:
        content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        content.append(Gtk.Label(label="Color"))
        self.color_preview = Gtk.DrawingArea()
        self.color_preview.set_content_width(14)
        self.color_preview.set_content_height(14)
        self.color_preview.set_draw_func(self._draw_color_preview)
        content.append(self.color_preview)
        return content

    def _draw_color_preview(
        self,
        _area: Gtk.DrawingArea,
        context,
        width: int,
        height: int,
    ) -> None:
        color = self.drawing_color.current
        context.rectangle(1, 1, width - 2, height - 2)
        context.set_source_rgb(*color)
        context.fill_preserve()
        context.set_source_rgb(0.35, 0.35, 0.35)
        context.set_line_width(1)
        context.stroke()

    def _on_drawing_color_changed(self, color: Color) -> None:
        if self.color_preview is not None:
            self.color_preview.queue_draw()
        if self._active_text_box is not None:
            self._active_text_box.apply_color_to_selection(color)

    def _on_eraser_toggled(self, button: Gtk.ToggleButton) -> None:
        if button.get_active() and self.tool_buttons["Pen"].get_active():
            self.tool_buttons["Pen"].set_active(False)
        if button.get_active() and self.tool_buttons["Text Box"].get_active():
            self.tool_buttons["Text Box"].set_active(False)
        self.eraser.set_enabled(button.get_active())

    def _on_text_box_toggled(self, button: Gtk.ToggleButton) -> None:
        if button.get_active() and self.tool_buttons["Pen"].get_active():
            self.tool_buttons["Pen"].set_active(False)
        if button.get_active() and self.tool_buttons["Eraser"].get_active():
            self.tool_buttons["Eraser"].set_active(False)

    def _on_canvas_pressed(
        self,
        _gesture: Gtk.GestureClick,
        press_count: int,
        x: float,
        y: float,
    ) -> None:
        if press_count != 1:
            return
        self.board.grab_focus()
        self._clear_text_box_highlight()
        if not self.tool_buttons["Text Box"].get_active():
            return
        position = self.zoom.to_board(x, y)
        text_box = TextBox(
            self.board,
            self.drawing_color,
            self.zoom,
            position,
            self._set_active_text_box,
            self._on_text_box_blur,
            self._ensure_text_box_extent,
        )
        self.text_boxes.append(text_box)
        self._set_active_text_box(text_box)
        self._ensure_text_box_extent(text_box)
        self.tool_buttons["Text Box"].set_active(False)

    def _set_active_text_box(self, text_box: TextBox) -> None:
        if (
            self._highlighted_text_box is not None
            and self._highlighted_text_box is not text_box
        ):
            self._highlighted_text_box.set_highlighted(False)
        self._active_text_box = text_box
        self._highlighted_text_box = text_box
        text_box.set_highlighted(True)

    def _on_text_box_blur(self, text_box: TextBox) -> None:
        if self._highlighted_text_box is text_box:
            self._highlighted_text_box = None
            text_box.set_highlighted(False)

    def _clear_text_box_highlight(self) -> None:
        if self._highlighted_text_box is not None:
            self._highlighted_text_box.set_highlighted(False)
            self._highlighted_text_box = None

    def _on_toolbar_button_clicked(self, _button: Gtk.Widget) -> None:
        self._clear_text_box_highlight()
        self.board.grab_focus()

    def _on_color_menu_active(
        self, _button: Gtk.MenuButton, _property: object
    ) -> None:
        self._clear_text_box_highlight()
        self.board.grab_focus()

    def _ensure_text_box_extent(self, text_box: TextBox) -> None:
        right = math.ceil(text_box.x + text_box.width)
        bottom = math.ceil(text_box.y + text_box.height)
        if right > self._canvas_width:
            self._set_canvas_extent("width", right)
        if bottom > self._canvas_height:
            self._set_canvas_extent("height", bottom)

    def _update_history_buttons(self) -> None:
        self.tool_buttons["Undo"].set_sensitive(self.pen.can_undo)
        self.tool_buttons["Redo"].set_sensitive(self.pen.can_redo)

    def _initialize_scrollable_canvas(self, _scroller: Gtk.ScrolledWindow) -> None:
        horizontal = self.canvas_scroller.get_hadjustment()
        vertical = self.canvas_scroller.get_vadjustment()
        horizontal.connect(
            "value-changed", self._extend_canvas_for_scroll, "width"
        )
        horizontal.connect("changed", self._extend_canvas_for_scroll, "width")
        vertical.connect(
            "value-changed", self._extend_canvas_for_scroll, "height"
        )
        vertical.connect("changed", self._extend_canvas_for_scroll, "height")
        self._extend_canvas_to_page(horizontal, "width")
        self._extend_canvas_to_page(vertical, "height")

    def _extend_canvas_for_scroll(
        self, adjustment: Gtk.Adjustment, dimension: str
    ) -> None:
        if self._extending_canvas:
            return
        page_size = int(adjustment.get_page_size())
        if page_size <= 0:
            return
        extent = self._canvas_width if dimension == "width" else self._canvas_height
        page_extent = math.ceil(page_size / self.zoom.scale)
        if extent == 0 or adjustment.get_upper() - adjustment.get_value() <= (
            page_size * 1.25
        ):
            self._set_canvas_extent(dimension, extent + page_extent)

    def _extend_canvas_to_page(
        self, adjustment: Gtk.Adjustment, dimension: str
    ) -> None:
        page_size = int(adjustment.get_page_size())
        if page_size > 0:
            page_extent = math.ceil(page_size / self.zoom.scale)
            extent = self._canvas_width if dimension == "width" else self._canvas_height
            self._set_canvas_extent(dimension, max(extent, page_extent * 2))

    def _set_canvas_extent(self, dimension: str, extent: int) -> None:
        self._extending_canvas = True
        if dimension == "width":
            self._canvas_width = extent
            self.canvas.set_content_width(self.zoom.to_pixels(extent))
        else:
            self._canvas_height = extent
            self.canvas.set_content_height(self.zoom.to_pixels(extent))
        self.board.set_size_request(
            self.zoom.to_pixels(self._canvas_width),
            self.zoom.to_pixels(self._canvas_height),
        )
        self._extending_canvas = False
