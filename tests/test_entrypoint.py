"""Entry-point tests for the project bootstrap.

These checks keep the initial package launch path stable while the application
is still in its early GTK bootstrap phase.
"""

import os
import runpy

import gi

gi.require_version("GLib", "2.0")
from gi.repository import GLib

from codevision.app.main_window import _launch_external_uri
from codevision.main import _configure_display_backend, _configure_session_bus


def test_configure_session_bus_uses_runtime_socket_when_disabled(
    monkeypatch, tmp_path
):
    bus_socket = tmp_path / "bus"
    bus_socket.touch()
    monkeypatch.setenv("DBUS_SESSION_BUS_ADDRESS", "disabled:")
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))

    _configure_session_bus()

    assert os.environ["DBUS_SESSION_BUS_ADDRESS"] == f"unix:path={bus_socket}"


def test_configure_display_backend_prefers_x11_when_both_are_enabled(monkeypatch):
    monkeypatch.setenv("DISPLAY", ":0")
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
    monkeypatch.setenv("GDK_BACKEND", "wayland,x11")

    _configure_display_backend()

    assert os.environ["GDK_BACKEND"] == "x11"


def test_configure_display_backend_preserves_explicit_single_backend(monkeypatch):
    monkeypatch.setenv("DISPLAY", ":0")
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
    monkeypatch.setenv("GDK_BACKEND", "wayland")

    _configure_display_backend()

    assert os.environ["GDK_BACKEND"] == "wayland"


def test_codevision_module_entrypoint_exits_with_main_result(monkeypatch):
    calls = []
    monkeypatch.setattr("codevision.main.main", lambda: calls.append(True) or 7)

    try:
        runpy.run_module("codevision", run_name="__main__")
    except SystemExit as exc:
        assert exc.code == 7
    else:
        raise AssertionError("Expected the module entrypoint to raise SystemExit")

    assert calls == [True]


def test_external_uri_uses_in_app_browser_when_system_launch_fails():
    uri = "https://github.com/Algorift169/code-vision"
    opened = []
    statuses = []

    def launch_default(_uri):
        raise GLib.Error.new_literal(
            GLib.quark_from_string("g-io-error-quark"),
            "Operation not supported",
            15,
        )

    _launch_external_uri(uri, opened.append, statuses.append, launch_default)

    assert opened == [uri]
    assert statuses == []


def test_external_uri_reports_in_app_browser_failure():
    statuses = []

    def launch_default(_uri):
        return False

    def open_in_app(_uri):
        raise RuntimeError("Browser unavailable")

    _launch_external_uri(
        "https://github.com/Algorift169/code-vision",
        open_in_app,
        statuses.append,
        launch_default,
    )

    assert statuses == ["Could not open link: Browser unavailable"]
