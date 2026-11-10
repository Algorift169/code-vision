from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from .analyzer_theme import AnalyzerTheme

SECTIONS = (
    "Overview",
    "AST",
    "Flowchart",
    "Call Graph",
    "Var Flow",
    "Complexity",
    "Warnings",
    "Export",
)


class AnalysisPanel(Gtk.Box):
    """Right-side analysis panel with navigable empty section placeholders."""

    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._analyzer_theme = AnalyzerTheme()
        self.set_name("analysis-panel")
        self.add_css_class("panel")
        self.set_vexpand(True)
        self.set_hexpand(True)
        self.set_size_request(0, -1)
        self.set_margin_top(0)
        self.set_margin_bottom(0)
        self.current_section = SECTIONS[0]
        self._section_buttons: dict[str, Gtk.ToggleButton] = {}

        self.navigation = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=4
        )
        self.navigation.add_css_class("analysis-navigation")

        first_button: Gtk.ToggleButton | None = None
        for section in SECTIONS:
            button = Gtk.ToggleButton(label=section)
            button.add_css_class("analysis-nav-button")
            button.set_focusable(True)
            button.set_tooltip_text(section)
            if first_button is None:
                first_button = button
            else:
                button.set_group(first_button)
            button.connect("toggled", self._on_section_toggled, section)
            self.navigation.append(button)
            self._section_buttons[section] = button

        nav_scroller = Gtk.ScrolledWindow()
        nav_scroller.set_name("analysis-navigation-scroller")
        nav_scroller.add_css_class("analysis-navigation-scroller")
        nav_scroller.set_policy(
            Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER
        )
        nav_scroller.set_min_content_height(40)
        nav_scroller.set_max_content_height(40)
        nav_scroller.set_hexpand(True)
        nav_scroller.set_child(self.navigation)
        self.append(nav_scroller)

        self.views = Gtk.Stack()
        self.views.set_name("analysis-section-views")
        self.views.add_css_class("analysis-section-views")
        self.views.set_transition_type(Gtk.StackTransitionType.NONE)
        self.views.set_hexpand(True)
        self.views.set_vexpand(True)

        self._section_placeholders: dict[str, Gtk.Widget] = {}
        for index, section in enumerate(SECTIONS):
            placeholder = Gtk.Box(
                orientation=Gtk.Orientation.VERTICAL, spacing=0
            )
            placeholder.add_css_class("analysis-placeholder")
            placeholder.set_hexpand(True)
            placeholder.set_vexpand(True)

            title = Gtk.Label(label=section)
            title.add_css_class("analysis-placeholder-title")
            title.set_halign(Gtk.Align.CENTER)
            title.set_valign(Gtk.Align.CENTER)
            title.set_hexpand(True)
            title.set_vexpand(True)
            placeholder.append(title)

            page_name = f"section-{index}"
            self.views.add_named(placeholder, page_name)
            self._section_placeholders[section] = placeholder

        self.append(self.views)
        self.select_section(SECTIONS[0])

    @property
    def sections(self) -> tuple[str, ...]:
        return SECTIONS

    @property
    def section_buttons(self) -> dict[str, Gtk.ToggleButton]:
        return self._section_buttons.copy()

    def select_section(self, section: str) -> None:
        if section not in self._section_buttons:
            raise ValueError(f"Unknown analysis section: {section}")
        self._section_buttons[section].set_active(True)

    def _on_section_toggled(
        self, button: Gtk.ToggleButton, section: str
    ) -> None:
        if not button.get_active():
            return
        self.current_section = section
        self.views.set_visible_child(self._section_placeholders[section])
