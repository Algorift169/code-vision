from __future__ import annotations

import sys

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from .main_window import CodeVisionWindow


class CodeVisionApplication(Gtk.Application):
    """Own GTK startup, window activation, and application shutdown."""

    def __init__(self) -> None:
        super().__init__(application_id="org.codevision.app")
        self.startup_error: RuntimeError | None = None

    def do_activate(self) -> None:
        try:
            window = CodeVisionWindow(self)
            window.present()
        except RuntimeError as error:
            self.startup_error = error
            self.quit()


def main() -> int:
    """Initialize GTK and run the desktop application."""
    try:
        application = CodeVisionApplication()
        result = application.run()
    except (ImportError, ValueError, RuntimeError) as error:
        print(f"Failed to initialize CodeVision GTK UI: {error}", file=sys.stderr)
        return 1

    if application.startup_error is not None:
        print(
            f"Failed to initialize CodeVision GTK UI: {application.startup_error}",
            file=sys.stderr,
        )
        return 1
    return result
