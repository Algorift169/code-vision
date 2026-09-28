from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path


class ManagedTerminalService:
    """Launch and track only terminal processes started by CodeVision."""

    def __init__(
        self,
        find_executable: Callable[[str], str | None] = shutil.which,
        popen_factory: Callable[..., subprocess.Popen] = subprocess.Popen,
    ) -> None:
        self._find_executable = find_executable
        self._popen = popen_factory
        self._processes: list[subprocess.Popen] = []

    @property
    def has_running_terminal(self) -> bool:
        self._processes = [
            process for process in self._processes if process.poll() is None
        ]
        return bool(self._processes)

    @property
    def is_available(self) -> bool:
        return any(
            self._find_executable(name) is not None
            for name in ("xterm", "gnome-terminal", "x-terminal-emulator")
        )

    def open(self, directory: Path) -> subprocess.Popen:
        directory = directory.expanduser().resolve(strict=True)
        if not directory.is_dir():
            raise NotADirectoryError(directory)

        shell = os.environ.get("SHELL") or self._find_executable("bash") or "/bin/sh"
        xterm = self._find_executable("xterm")
        gnome_terminal = self._find_executable("gnome-terminal")
        terminal_emulator = self._find_executable("x-terminal-emulator")

        if xterm is not None:
            command = [xterm, "-e", shell]
        elif gnome_terminal is not None:
            command = [
                gnome_terminal,
                "--wait",
                f"--working-directory={directory}",
                "--",
                shell,
            ]
        elif terminal_emulator is not None:
            command = [terminal_emulator, "-e", shell]
        else:
            raise FileNotFoundError("No supported terminal emulator was found")

        process = self._popen(command, cwd=directory, start_new_session=True)
        self._processes.append(process)
        return process

    def kill_latest(self) -> bool:
        while self._processes and self._processes[-1].poll() is not None:
            self._processes.pop()
        if not self._processes:
            return False

        process = self._processes.pop()
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        return True
