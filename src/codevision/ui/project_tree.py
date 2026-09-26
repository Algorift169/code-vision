from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk


class ProjectTreePanel(Gtk.Box):
    """Sidebar tree view for workspace/project navigation."""

    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_name("project-panel")
        self.add_css_class("panel")
        self.set_size_request(220, -1)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header.set_margin_top(10)
        header.set_margin_bottom(10)
        header.set_margin_start(12)
        header.set_margin_end(12)
        header.add_css_class("panel-header")

        title = Gtk.Label(label="Project Explorer")
        title.set_halign(Gtk.Align.START)
        title.add_css_class("section-title")
        header.append(title)

        self.append(header)

        self.tree = Gtk.TreeView()
        self.tree.set_headers_visible(False)
        self.tree.set_enable_search(False)
        self.tree.set_activate_on_single_click(True)
        self.tree.set_hexpand(True)
        self.tree.set_vexpand(True)

        model = Gtk.TreeStore(str)
        self.tree.set_model(model)
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Name", renderer, text=0)
        column.set_expand(True)
        self.tree.append_column(column)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_child(self.tree)
        self.append(scrolled)
