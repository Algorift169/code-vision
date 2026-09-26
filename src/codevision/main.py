from __future__ import annotations

import sys


def main() -> int:
    """Minimal application entry point for the initial GTK bootstrap.

    This is intentionally small and does not yet implement the full UI. The goal
    is to confirm that the Python package can initialize the GTK runtime correctly
    and launch the application shell before any deeper analysis features are added.
    """
    try:
        import gi

        gi.require_version("Gtk", "4.0")
        from gi.repository import Gtk

        app = Gtk.Application(application_id="org.codevision.app")

        def on_activate(app: Gtk.Application) -> None:
            """Create the initial application window and present it to the user."""
            win = Gtk.ApplicationWindow(application=app)
            win.set_title("CodeVision")
            win.set_default_size(900, 600)
            win.present()

        app.connect("activate", on_activate)
        return app.run()
    except (ImportError, ValueError) as exc:
        print(f"Failed to initialize GTK 4: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
