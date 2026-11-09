from __future__ import annotations

import gi

gi.require_version("GdkPixbuf", "2.0")
gi.require_version("Gtk", "4.0")
from gi.repository import GdkPixbuf, Gtk

_ICON_KIND = {
    "document-new-symbolic": "file",
    "document-open-symbolic": "file",
    "text-x-generic-symbolic": "file",
    "folder-new-symbolic": "folder",
    "folder-symbolic": "folder",
    "utilities-terminal-symbolic": "terminal",
    "process-stop-symbolic": "stop",
    "go-up-symbolic": "up",
    "window-close-symbolic": "close",
    "view-refresh-symbolic": "refresh",
    "view-list-symbolic": "list",
    "view-split-left-right-symbolic": "split",
    "media-playback-start-symbolic": "play",
    "system-run-symbolic": "build",
    "edit-clear-symbolic": "clear",
}

_PIXBUF_PATHS = {
    "file": (
        "M4 1.8h6.8l3.7 3.7v10.7H4z "
        "M10.5 2.2v3.6h3.6 M6.5 9h5.5 M6.5 12h5.5"
    ),
    "folder": (
        "M1.8 4.5H7l1.7 1.9h7.5l-1.1 9.1H2.8z M2 6.4h14.2"
    ),
}


def create_symbolic_icon(
    icon_name: str, css_class: str, size: int = 18
) -> Gtk.DrawingArea:
    """Draw a small symbolic icon using the active GTK foreground color."""
    icon = Gtk.DrawingArea()
    icon.add_css_class("codevision-symbolic-icon")
    icon.add_css_class(css_class)
    icon.set_content_width(size)
    icon.set_content_height(size)
    icon.set_size_request(size, size)
    icon.set_valign(Gtk.Align.CENTER)
    icon.set_draw_func(_draw_icon, _ICON_KIND.get(icon_name, "action"))
    return icon


def create_symbolic_pixbuf(
    icon_name: str, color: str = "#3584e4", size: int = 18
) -> GdkPixbuf.Pixbuf:
    """Create a theme-independent file/folder icon for tree cell renderers."""
    kind = _ICON_KIND.get(icon_name, "file")
    if kind not in _PIXBUF_PATHS:
        kind = "file"
    path = _PIXBUF_PATHS[kind]
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="0 0 18 18"><path d="{path}" fill="none" stroke="{color}" '
        'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>'
        "</svg>"
    )
    loader = GdkPixbuf.PixbufLoader.new_with_type("svg")
    loader.write(svg.encode("utf-8"))
    loader.close()
    pixbuf = loader.get_pixbuf()
    if pixbuf is None:
        raise RuntimeError(f"Could not create {kind} icon")
    return pixbuf.copy()


def _draw_icon(
    widget: Gtk.DrawingArea,
    context: object,
    width: int,
    height: int,
    icon_kind: str,
) -> None:
    color = widget.get_style_context().get_color()
    context.set_source_rgba(color.red, color.green, color.blue, color.alpha)
    context.set_line_width(max(1.3, min(width, height) * 0.09))
    context.set_line_cap(1)
    context.set_line_join(1)

    scale_x = width / 18
    scale_y = height / 18
    context.scale(scale_x, scale_y)

    if icon_kind == "file":
        context.move_to(4, 1.8)
        context.line_to(10.8, 1.8)
        context.line_to(14.5, 5.5)
        context.line_to(14.5, 16.2)
        context.line_to(4, 16.2)
        context.close_path()
        context.move_to(10.5, 2.2)
        context.line_to(10.5, 5.8)
        context.line_to(14.1, 5.8)
        context.move_to(6.5, 9)
        context.line_to(12, 9)
        context.move_to(6.5, 12)
        context.line_to(12, 12)
        context.stroke()
    elif icon_kind == "folder":
        context.move_to(1.8, 4.5)
        context.line_to(7, 4.5)
        context.line_to(8.7, 6.4)
        context.line_to(16.2, 6.4)
        context.line_to(15.1, 15.5)
        context.line_to(2.8, 15.5)
        context.close_path()
        context.move_to(2, 6.4)
        context.line_to(16.2, 6.4)
        context.stroke()
    elif icon_kind == "terminal":
        context.rectangle(1.8, 2.5, 14.4, 13)
        context.stroke()
        context.move_to(4.5, 6.3)
        context.line_to(7, 8.6)
        context.line_to(4.5, 10.8)
        context.move_to(8.5, 11)
        context.line_to(12.5, 11)
        context.stroke()
    elif icon_kind == "stop":
        context.rectangle(3.2, 3.2, 11.6, 11.6)
        context.fill()
    elif icon_kind == "up":
        context.move_to(9, 15)
        context.line_to(9, 4)
        context.move_to(4.5, 8.5)
        context.line_to(9, 4)
        context.line_to(13.5, 8.5)
        context.stroke()
    elif icon_kind == "close":
        context.move_to(4.5, 4.5)
        context.line_to(13.5, 13.5)
        context.move_to(13.5, 4.5)
        context.line_to(4.5, 13.5)
        context.stroke()
    elif icon_kind == "refresh":
        context.arc(9, 9, 5.5, 0.6, 5.3)
        context.stroke()
        context.move_to(12.8, 3.5)
        context.line_to(15.5, 3.5)
        context.line_to(15.5, 6.2)
        context.close_path()
        context.fill()
    elif icon_kind == "list":
        for y in (4.5, 8.8, 13.1):
            context.move_to(3, y)
            context.line_to(15, y)
        context.stroke()
    elif icon_kind == "split":
        context.move_to(9, 2.5)
        context.line_to(9, 15.5)
        context.move_to(4, 5)
        context.line_to(7, 5)
        context.line_to(7, 8)
        context.move_to(14, 13)
        context.line_to(11, 13)
        context.line_to(11, 10)
        context.stroke()
    elif icon_kind == "play":
        context.move_to(5, 3)
        context.line_to(14.5, 9)
        context.line_to(5, 15)
        context.close_path()
        context.fill()
    elif icon_kind == "build":
        context.move_to(4, 14)
        context.line_to(13, 5)
        context.move_to(9, 3.5)
        context.line_to(14.5, 9)
        context.move_to(3, 10)
        context.line_to(8, 15)
        context.stroke()
    elif icon_kind == "clear":
        context.move_to(4, 5)
        context.line_to(14, 5)
        context.move_to(6, 5)
        context.line_to(6, 14)
        context.line_to(12, 14)
        context.line_to(12, 5)
        context.move_to(7.5, 3)
        context.line_to(10.5, 3)
        context.move_to(8, 7.5)
        context.line_to(8, 11.5)
        context.move_to(10, 7.5)
        context.line_to(10, 11.5)
        context.stroke()
    else:
        context.arc(9, 9, 6.6, 0, 6.283185307179586)
        context.move_to(9, 5)
        context.line_to(9, 9)
        context.line_to(12, 11)
        context.stroke()


__all__ = ["create_symbolic_icon"]
