"""List directory entries and navigate parent paths for the folder picker."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class BrowserEntry:
    """Describe one file or directory shown in the folder picker.

    The entry stores the display name, filesystem path, and whether the path
    resolves to a directory.
    """

    name: str
    path: Path
    is_directory: bool


class FolderBrowserService:
    """Provide directory listing and parent-navigation operations.

    The service returns lightweight entry records and leaves presentation,
    selection, and error handling to the folder-picker UI.
    """

    def list_entries(
        self, directory: Path, *, show_hidden: bool
    ) -> list[BrowserEntry]:
        """List a directory with folders first and names sorted case-insensitively.

        Hidden entries whose names begin with a dot are excluded unless
        ``show_hidden`` is true. Directory checks follow symbolic links, and
        any scanning or entry-inspection errors propagate to the caller.

        Args:
            directory: Directory whose immediate children should be listed.
            show_hidden: Include dot-prefixed names when true.

        Returns:
            Entry records sorted with directories before files, then by
            case-folded name.

        Raises:
            NotADirectoryError: If the expanded path is not a directory.
            OSError: If the directory cannot be scanned or an entry cannot
                be inspected.
        """
        directory = directory.expanduser()
        if not directory.is_dir():
            raise NotADirectoryError(directory)

        entries: list[BrowserEntry] = []
        with os.scandir(directory) as items:
            for item in items:
                if not show_hidden and item.name.startswith("."):
                    continue
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
        """Return the resolved parent directory unless already at the root.

        The input is expanded and resolved before its parent is calculated.
        A filesystem root returns ``None`` because it has no distinct parent.
        """
        directory = directory.expanduser().resolve()
        parent = directory.parent
        return None if parent == directory else parent
