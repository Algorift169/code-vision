from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class BrowserEntry:
    """A file or directory shown by the in-app folder picker."""

    name: str
    path: Path
    is_directory: bool


class FolderBrowserService:
    """Filesystem operations used by the in-app folder picker."""

    def list_entries(self, directory: Path) -> list[BrowserEntry]:
        directory = directory.expanduser()
        if not directory.is_dir():
            raise NotADirectoryError(directory)

        entries: list[BrowserEntry] = []
        with os.scandir(directory) as items:
            for item in items:
                entries.append(
                    BrowserEntry(
                        name=item.name,
                        path=Path(item.path),
                        is_directory=item.is_dir(follow_symlinks=True),
                    )
                )

        return sorted(
            entries,
            key=lambda entry: (not entry.is_directory, entry.name.casefold()),
        )

    def parent_directory(self, directory: Path) -> Path | None:
        directory = directory.expanduser().resolve()
        parent = directory.parent
        return None if parent == directory else parent
