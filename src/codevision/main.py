from __future__ import annotations

import sys


def main() -> int:
    """Launch the CodeVision application window with the workspace layout."""
    try:
        import gi

        gi.require_version("Gtk", "4.0")
        from gi.repository import Gtk

        from codevision.ui.main_window import CodeVisionWindow

        app = Gtk.Application(application_id="org.codevision.app")

        def on_activate(app: Gtk.Application) -> None:
            win = CodeVisionWindow(app)
            win.present()

        app.connect("activate", on_activate)
        return app.run()
    except (ImportError, ValueError, RuntimeError) as exc:
        print(f"Failed to initialize CodeVision GTK UI: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
