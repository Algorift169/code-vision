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

""" This function is a callback that is called when the application is 
activated. It creates a new application window, sets its title and default size, 
and presents it to the user. """
        def on_activate(app: Gtk.Application) -> None:
            # The first milestone is just proving the GTK app can open a window.
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
