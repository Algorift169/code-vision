from __future__ import annotations

import os
import shutil
import signal
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib, Gtk

try:
    gi.require_version("Vte", "3.91")
    from gi.repository import Vte
except (ImportError, ValueError):
    Vte = None

@dataclass(slots=True)
class TerminalSession:
    terminal: Gtk.Widget
    directory: Path
    process_id: int | None = None
    exited: bool = False
    error: str | None = None


class TerminalService:
    """Create embedded VTE terminal sessions and manage only their child shells."""

    def __init__(
        self,
        terminal_factory: Callable[[], Gtk.Widget] | None = None,
        kill_process: Callable[[int, int], None] = os.kill,
    ) -> None:
        self._terminal_factory = terminal_factory or (
            Vte.Terminal if Vte is not None else None
        )
        self._kill_process = kill_process
        self._sessions: list[TerminalSession] = []

    @property
    def is_available(self) -> bool:
        return self._terminal_factory is not None and self._shell() is not None

    @property
    def has_running_terminal(self) -> bool:
        return any(
            session.process_id is not None and not session.exited
            for session in self._sessions
        )

    def open(self, directory: Path) -> TerminalSession:
        directory = directory.expanduser().resolve(strict=True)
        if not directory.is_dir():
            raise NotADirectoryError(directory)
        if self._terminal_factory is None:
            raise RuntimeError("Install the GTK 4 VTE terminal bindings to open a terminal")

        shell = self._shell()
        if shell is None:
            raise FileNotFoundError("No supported shell was found")

        terminal = self._terminal_factory()
        terminal.set_hexpand(True)
        terminal.set_vexpand(True)
        terminal.set_scrollback_lines(10000)
        session = TerminalSession(terminal=terminal, directory=directory)
        self._sessions.append(session)
        terminal.connect("child-exited", self._on_child_exited, session)

        try:
            terminal.spawn_async(
                pty_flags=Vte.PtyFlags.DEFAULT if Vte is not None else 0,
                working_directory=str(directory),
                argv=[shell],
                envv=None,
                spawn_flags=GLib.SpawnFlags.DEFAULT,
                child_setup=None,
                timeout=-1,
                cancellable=Gio.Cancellable(),
                callback=self._on_spawned,
                user_data=session,
            )
        except (GLib.Error, OSError) as error:
            session.error = str(error)
            session.exited = True
            self._sessions.remove(session)
            raise RuntimeError(f"Could not start terminal: {error}") from error
        return session

    def kill_latest(self) -> bool:
        session = next(
            (
                item
                for item in reversed(self._sessions)
                if item.process_id is not None and not item.exited
            ),
            None,
        )
        return self.close(session) if session is not None else False

    def close(self, session: TerminalSession) -> bool:
        if session not in self._sessions:
            return False
        process_id = session.process_id
        session.exited = True
        self._sessions.remove(session)
        if process_id is None:
            return True
        try:
            self._kill_process(process_id, signal.SIGTERM)
        except ProcessLookupError:
            pass
        return True

    def close_all(self) -> None:
        for session in tuple(self._sessions):
            self.close(session)

    @staticmethod
    def _shell() -> str | None:
        configured_shell = os.environ.get("SHELL")
        if configured_shell and Path(configured_shell).is_file():
            return configured_shell
        return shutil.which("bash") or shutil.which("sh")

    def _on_spawned(
        self,
        terminal: Gtk.Widget,
        process_id: int,
        error: GLib.Error | None,
        session: TerminalSession,
    ) -> None:
        if error is not None or process_id <= 0:
            session.error = str(error or "Terminal shell failed to start")
            session.exited = True
            return
        session.process_id = process_id
        if session.exited:
            try:
                self._kill_process(process_id, signal.SIGTERM)
            except ProcessLookupError:
                pass
            return
        terminal.watch_child(process_id)

    @staticmethod
    def _on_child_exited(
        _terminal: Gtk.Widget,
        _exit_status: int,
        session: TerminalSession,
    ) -> None:
        session.exited = True
