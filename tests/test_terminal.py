from pathlib import Path
from signal import SIGTERM

from codevision.services.terminal import TerminalService


class FakeTerminal:
    def __init__(self, *, complete_spawn: bool = True) -> None:
        self.signals = {}
        self.spawn_args = None
        self.spawn_kwargs = None
        self.watched_pid = None
        self.complete_spawn = complete_spawn

    def set_hexpand(self, _value: bool) -> None:
        pass

    def set_vexpand(self, _value: bool) -> None:
        pass

    def set_scrollback_lines(self, _lines: int) -> None:
        pass

    def connect(self, name: str, callback: object, data: object) -> None:
        self.signals[name] = (callback, data)

    def spawn_async(self, *args: object, **kwargs: object) -> None:
        self.spawn_args = args
        self.spawn_kwargs = kwargs
        if self.complete_spawn:
            callback = kwargs["callback"]
            callback(self, 2468, None, kwargs["user_data"])

    def watch_child(self, process_id: int) -> None:
        self.watched_pid = process_id

    def finish_child(self, status: int = 0) -> None:
        callback, data = self.signals["child-exited"]
        callback(self, status, data)


def test_terminal_service_creates_embedded_session_in_project_directory(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "project with spaces"
    directory.mkdir()
    terminal = FakeTerminal()
    killed: list[tuple[int, int]] = []
    service = TerminalService(
        terminal_factory=lambda: terminal,
        kill_process=lambda process_id, sig: killed.append((process_id, sig)),
    )

    session = service.open(directory)

    assert session.terminal is terminal
    assert session.directory == directory.resolve()
    assert terminal.spawn_kwargs["working_directory"] == str(directory.resolve())
    assert terminal.spawn_kwargs["timeout"] == -1
    assert terminal.spawn_kwargs["cancellable"] is not None
    assert terminal.watched_pid == 2468
    assert service.has_running_terminal
    assert service.kill_latest()
    assert killed == [(2468, SIGTERM)]
    assert not service.has_running_terminal


def test_closed_session_terminates_shell_after_async_spawn(tmp_path: Path) -> None:
    directory = tmp_path / "project"
    directory.mkdir()
    terminal = FakeTerminal(complete_spawn=False)
    killed: list[tuple[int, int]] = []
    service = TerminalService(
        terminal_factory=lambda: terminal,
        kill_process=lambda process_id, sig: killed.append((process_id, sig)),
    )

    session = service.open(directory)
    assert service.close(session)
    callback = terminal.spawn_kwargs["callback"]
    callback(terminal, 1357, None, terminal.spawn_kwargs["user_data"])

    assert killed == [(1357, SIGTERM)]
    assert not service.has_running_terminal


def test_child_exit_removes_session_from_running_state(tmp_path: Path) -> None:
    directory = tmp_path / "project"
    directory.mkdir()
    terminal = FakeTerminal()
    service = TerminalService(terminal_factory=lambda: terminal)
    session = service.open(directory)

    terminal.finish_child()

    assert session.exited
    assert not service.has_running_terminal
    assert not service.kill_latest()
