import os
from pathlib import Path

from codevision.services.managed_terminal import ManagedTerminalService


class FakeProcess:
    def __init__(self) -> None:
        self.terminated = False
        self.killed = False

    def poll(self) -> int | None:
        return 0 if self.terminated or self.killed else None

    def terminate(self) -> None:
        self.terminated = True

    def wait(self, timeout: int | None = None) -> int:
        return 0

    def kill(self) -> None:
        self.killed = True


def test_terminal_uses_path_arguments_and_tracks_owned_process(tmp_path: Path) -> None:
    directory = tmp_path / "project with spaces"
    directory.mkdir()
    process = FakeProcess()
    calls: list[tuple[list[str], dict[str, object]]] = []

    def find_executable(name: str) -> str | None:
        return "/usr/bin/xterm" if name == "xterm" else None

    def popen(command: list[str], **kwargs: object) -> FakeProcess:
        calls.append((command, kwargs))
        return process

    service = ManagedTerminalService(find_executable, popen)
    service.open(directory)

    assert calls[0][0] == [
        "/usr/bin/xterm",
        "-e",
        os.environ.get("SHELL") or "/bin/sh",
    ]
    assert calls[0][1]["cwd"] == directory.resolve()
    assert service.has_running_terminal
    assert service.kill_latest()
    assert process.terminated
    assert not service.has_running_terminal


def test_kill_terminal_does_not_touch_unmanaged_processes() -> None:
    service = ManagedTerminalService(find_executable=lambda _name: None)

    assert not service.kill_latest()
