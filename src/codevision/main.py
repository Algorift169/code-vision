"""Thin command-line entry point for CodeVision."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _configure_session_bus() -> None:
    if os.environ.get("DBUS_SESSION_BUS_ADDRESS") != "disabled:":
        return
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
    if runtime_dir is None:
        return
    bus_socket = Path(runtime_dir) / "bus"
    if bus_socket.exists():
        os.environ["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path={bus_socket}"


def _configure_renderer() -> None:
    # On Linux Wayland/X11 with Intel graphics, GTK4's default Vulkan renderer
    # triggers incomplete Mesa format modifier handling ('FINISHME: support YUV
    # colorspace with DRM format modifiers'), which breaks composited webview textures.
    # Defaulting GSK_RENDERER to 'ngl' routes through stable accelerated OpenGL.
    if "GSK_RENDERER" not in os.environ:
        os.environ["GSK_RENDERER"] = "ngl"


def _configure_display_backend() -> None:
    configured = os.environ.get("GDK_BACKEND", "")
    backends = {backend.strip() for backend in configured.split(",") if backend.strip()}
    if os.environ.get("DISPLAY") and {"x11", "wayland"} <= backends:
        os.environ["GDK_BACKEND"] = "x11"
        return
    if configured:
        return
    if os.environ.get("DISPLAY"):
        os.environ["GDK_BACKEND"] = "x11"
    elif os.environ.get("WAYLAND_DISPLAY"):
        os.environ["GDK_BACKEND"] = "wayland"
    else:
        os.environ["GDK_BACKEND"] = "x11"


def main() -> int:
    """Delegate startup to the application lifecycle package."""
    _configure_session_bus()
    _configure_renderer()
    _configure_display_backend()
    if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        print(
            "CodeVision needs an active X11 or Wayland desktop session. "
            "No display server is available in this environment.",
            file=sys.stderr,
        )
        return 1
    try:
        from .app.application import main as run_application
    except (ImportError, ValueError, RuntimeError) as error:
        print(f"Failed to initialize CodeVision GTK UI: {error}", file=sys.stderr)
        return 1

    return run_application()


if __name__ == "__main__":
    raise SystemExit(main())
