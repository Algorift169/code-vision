from pathlib import Path

import gi
import pytest

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from codevision.ui.theme import THEMES, ThemeManager, TRANSPARENT_THEME_ID
from codevision.ui.widgets.menu import ContextMenu
from codevision.ui.widgets.menu_actions import change_theme
from codevision.ui.widgets.menu_context import MenuContext
from codevision.ui.widgets.theme_menu import ThemeMenu


STYLES_DIRECTORY = Path(__file__).resolve().parents[1] / "resources" / "styles"


def test_all_themes_have_a_stylesheet() -> None:
    assert len(THEMES) == 13
    assert all((STYLES_DIRECTORY / theme.stylesheet).is_file() for theme in THEMES)


def test_theme_choice_is_applied_and_persisted(tmp_path: Path) -> None:
    preferences_file = tmp_path / "config" / "theme"
    manager = ThemeManager(STYLES_DIRECTORY, preferences_file)

    manager.apply("light-sky")

    assert manager.current_theme == "light-sky"
    assert preferences_file.read_text(encoding="utf-8") == "light-sky"
    assert ThemeManager(STYLES_DIRECTORY, preferences_file).current_theme == "light-sky"


def test_transparency_preference_is_persisted_and_validated(tmp_path: Path) -> None:
    preferences_file = tmp_path / "theme"
    transparency_file = tmp_path / "theme-transparency"
    manager = ThemeManager(
        STYLES_DIRECTORY, preferences_file, transparency_file
    )

    assert manager.transparency_percent == 30
    manager.set_transparency_percent(65)

    reloaded = ThemeManager(
        STYLES_DIRECTORY, preferences_file, transparency_file
    )
    assert reloaded.transparency_percent == 65
    with pytest.raises(ValueError, match="between 0 and 90"):
        manager.set_transparency_percent(100)


def test_unknown_theme_is_rejected(tmp_path: Path) -> None:
    manager = ThemeManager(STYLES_DIRECTORY, tmp_path / "theme")

    with pytest.raises(ValueError, match="Unknown theme"):
        manager.apply("not-a-theme")


def test_change_theme_action_opens_theme_menu_not_a_dialog() -> None:
    opened: list[Gtk.Widget] = []
    context = MenuContext(
        widget=Gtk.Box(),
        kind="window",
        theme_manager=object(),
        open_theme_menu=opened.append,
    )

    assert change_theme.is_enabled(context)
    change_theme.run(context)

    assert opened == [context.widget]


def test_context_menu_change_theme_opens_theme_menu() -> None:
    overlay = Gtk.Overlay()
    content = Gtk.Box()
    overlay.set_child(content)
    opened: list[Gtk.Widget] = []
    context = MenuContext(
        widget=content,
        kind="window",
        theme_manager=object(),
        open_theme_menu=opened.append,
    )
    menu = ContextMenu(overlay, content, lambda _x, _y: context)
    menu._context = context
    change_theme_button = menu._items["change-theme"][0]
    menu.set_visible(True)

    menu._on_action_clicked(change_theme_button, "change-theme")

    assert opened == [change_theme_button]
    assert not menu.get_visible()


def test_theme_menu_applies_selection_and_closes(tmp_path: Path) -> None:
    class StatusLabel:
        text = ""

        def set_text(self, text: str) -> None:
            self.text = text

    class ThemeWindow:
        def __init__(self) -> None:
            self.theme_manager = ThemeManager(
                STYLES_DIRECTORY, tmp_path / "theme"
            )
            self.status_label = StatusLabel()

        def set_theme(self, theme_id: str) -> None:
            self.theme_manager.apply(theme_id)

        def set_transparency_percent(self, percentage: int) -> None:
            self.theme_manager.set_transparency_percent(percentage)

    window = ThemeWindow()
    overlay = Gtk.Overlay()
    menu = ThemeMenu(window, overlay)
    menu.set_visible(True)

    menu._on_theme_selected(menu._theme_items["light-sky"][0], "light-sky")

    assert window.theme_manager.current_theme == "light-sky"
    assert window.status_label.text == "Theme: Light Sky"
    assert not menu.get_visible()


def test_transparent_theme_opens_adjustable_transparency_controls(
    tmp_path: Path,
) -> None:
    class StatusLabel:
        text = ""

        def set_text(self, text: str) -> None:
            self.text = text

    class ThemeWindow:
        def __init__(self) -> None:
            self.theme_manager = ThemeManager(
                STYLES_DIRECTORY, tmp_path / "theme", tmp_path / "transparency"
            )
            self.status_label = StatusLabel()

        def set_theme(self, theme_id: str) -> None:
            self.theme_manager.apply(theme_id)

        def set_transparency_percent(self, percentage: int) -> None:
            self.theme_manager.set_transparency_percent(percentage)

    window = ThemeWindow()
    overlay = Gtk.Overlay()
    menu = ThemeMenu(window, overlay)
    menu.set_visible(True)

    menu._on_theme_selected(
        menu._theme_items[TRANSPARENT_THEME_ID][0], TRANSPARENT_THEME_ID
    )

    assert window.theme_manager.current_theme == TRANSPARENT_THEME_ID
    assert menu._transparency_panel.get_visible()
    assert menu.get_visible()

    menu._transparency_scale.set_value(55)

    assert window.theme_manager.transparency_percent == 55
    assert menu._transparency_label.get_text() == "55%"

    menu._on_transparency_applied(Gtk.Button())
    assert not menu.get_visible()
