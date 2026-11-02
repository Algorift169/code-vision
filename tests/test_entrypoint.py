"""Entry-point tests for the project bootstrap.

These checks keep the initial package launch path stable while the application
is still in its early GTK bootstrap phase.
"""

import os
import runpy

from codevision.main import _configure_session_bus


def test_configure_session_bus_uses_runtime_socket_when_disabled(
    monkeypatch, tmp_path
):
    bus_socket = tmp_path / "bus"
    bus_socket.touch()
    monkeypatch.setenv("DBUS_SESSION_BUS_ADDRESS", "disabled:")
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))

    _configure_session_bus()

    assert os.environ["DBUS_SESSION_BUS_ADDRESS"] == f"unix:path={bus_socket}"


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
