from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
gi.require_version("GLib", "2.0")
from gi.repository import Gdk, GLib, Gtk


@dataclass(frozen=True, slots=True)
class Theme:
    theme_id: str
    name: str
    stylesheet: str


THEMES = (
    Theme("obsidian-forge", "Obsidian Forge", "theme-obsidian-forge.css"),
    Theme("cyber-neon", "Cyber Neon", "theme-cyber-neon.css"),
    Theme("midnight-aurora", "Midnight Aurora", "theme-midnight-aurora.css"),
    Theme("monochrome-pro", "Monochrome Pro", "theme-monochrome-pro.css"),
    Theme("dark-high-contrast", "Dark High Contrast", "theme-dark-high-contrast.css"),
    Theme("paper-ink", "Paper & Ink", "theme-paper-ink.css"),
    Theme("light-sky", "Light Sky", "theme-light-sky.css"),
    Theme("matrix-terminal", "Matrix Terminal", "theme-matrix-terminal.css"),
    Theme("copper-circuit", "Copper Circuit", "theme-copper-circuit.css"),
    Theme("arctic-glass", "Arctic Glass", "theme-arctic-glass.css"),
    Theme("crimson-core", "Crimson Core", "theme-crimson-core.css"),
    Theme("blueprint", "Blueprint", "theme-blueprint.css"),
)


class ThemeManager:
    """Load, apply, and persist the user's CodeVision color theme."""

    def __init__(
        self,
        styles_directory: Path | None = None,
        preferences_file: Path | None = None,
    ) -> None:
        self._styles_directory = styles_directory or self._default_styles_directory()
        self._preferences_file = preferences_file or (
            Path(GLib.get_user_config_dir()) / "codevision" / "theme"
        )
        self._display = Gdk.Display.get_default()
        self._provider: Gtk.CssProvider | None = None
        self.current_theme = self._load_preference()

    @staticmethod
    def _default_styles_directory() -> Path:
        source_styles = Path(__file__).resolve().parents[3] / "resources" / "styles"
        if source_styles.is_dir():
            return source_styles
        return Path.cwd() / "resources" / "styles"

    @staticmethod
    def theme_names() -> tuple[str, ...]:
        return tuple(theme.name for theme in THEMES)

    def _load_preference(self) -> str:
        try:
            theme_id = self._preferences_file.read_text(encoding="utf-8").strip()
        except OSError:
            return THEMES[0].theme_id
        return theme_id if self._theme_for_id(theme_id) is not None else THEMES[0].theme_id

    @staticmethod
    def _theme_for_id(theme_id: str) -> Theme | None:
        return next((theme for theme in THEMES if theme.theme_id == theme_id), None)

    def apply(self, theme_id: str) -> None:
        theme = self._theme_for_id(theme_id)
        if theme is None:
            raise ValueError(f"Unknown theme: {theme_id}")

        provider = Gtk.CssProvider()
        stylesheet = self._styles_directory / theme.stylesheet
        provider.load_from_path(str(stylesheet))
        if self._display is not None:
            if self._provider is not None:
                Gtk.StyleContext.remove_provider_for_display(
                    self._display, self._provider
                )
            Gtk.StyleContext.add_provider_for_display(
                self._display,
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1,
            )
        self._provider = provider
        self.current_theme = theme_id
        self._save_preference(theme_id)

    def _save_preference(self, theme_id: str) -> None:
        try:
            self._preferences_file.parent.mkdir(parents=True, exist_ok=True)
            self._preferences_file.write_text(theme_id, encoding="utf-8")
        except OSError:
            pass

    def show_dialog(self, parent: Gtk.Window | None = None) -> None:
        dialog = Gtk.Dialog(title="Change Theme", transient_for=parent, modal=True)
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("Apply", Gtk.ResponseType.ACCEPT)
        dialog.set_default_response(Gtk.ResponseType.ACCEPT)

        content = dialog.get_content_area()
        content.set_spacing(10)
        content.set_margin_top(16)
        content.set_margin_bottom(16)
        content.set_margin_start(16)
        content.set_margin_end(16)

        label = Gtk.Label(label="Application theme")
        label.set_halign(Gtk.Align.START)
        content.append(label)

        dropdown = Gtk.DropDown.new_from_strings(list(self.theme_names()))
        dropdown.set_selected(
            next(
                index
                for index, theme in enumerate(THEMES)
                if theme.theme_id == self.current_theme
            )
        )
        content.append(dropdown)

        def on_response(_dialog: Gtk.Dialog, response: int) -> None:
            if response == Gtk.ResponseType.ACCEPT:
                selected_theme = THEMES[dropdown.get_selected()]
                try:
                    self.apply(selected_theme.theme_id)
                except (OSError, GLib.Error, ValueError) as error:
                    dialog.set_title(f"Could not apply theme: {error}")
                    return
            dialog.close()

        dialog.connect("response", on_response)
        dialog.present()
