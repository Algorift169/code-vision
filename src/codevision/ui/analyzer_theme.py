from __future__ import annotations

from pathlib import Path

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gtk


class AnalyzerTheme:
    """Load the Analyzer Panel stylesheet from the shared styles directory."""

    _display: Gdk.Display | None = None
    _provider: Gtk.CssProvider | None = None

    def __init__(self) -> None:
        display = Gdk.Display.get_default()
        if display is None:
            return
        if self.__class__._display is display and self.__class__._provider is not None:
            return

        styles_directory = Path(__file__).resolve().parents[3] / "resources" / "styles"
        if not styles_directory.is_dir():
            styles_directory = Path.cwd() / "resources" / "styles"

        provider = Gtk.CssProvider()
        provider.load_from_path(str(styles_directory / "analyzer-theme.css"))
        if self.__class__._display is not None and self.__class__._provider is not None:
            Gtk.StyleContext.remove_provider_for_display(
                self.__class__._display,
                self.__class__._provider,
            )
        Gtk.StyleContext.add_provider_for_display(
            display,
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 2,
        )
        self.__class__._display = display
        self.__class__._provider = provider


__all__ = ["AnalyzerTheme"]
