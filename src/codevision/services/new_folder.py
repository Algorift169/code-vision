"""Create new directories in existing project locations."""

from __future__ import annotations

from pathlib import Path


class NewFolderService:
    """Create directories beneath an existing project directory.

    Folder names are validated as a single path component before a directory
    is created, avoiding accidental traversal outside the chosen parent.
    """

    def create(self, directory: Path, name: str) -> Path:
        """Create a folder and return its path beneath the resolved parent.

        The requested parent is expanded and resolved before validation and
        creation. ``Path.mkdir`` is called without ``parents`` or
        ``exist_ok``, so a missing parent or existing destination is reported
        rather than silently accepted.

        Args:
            directory: Existing directory in which to create the folder.
            name: New folder name without directory separators.

        Returns:
            The created folder path.

        Raises:
            NotADirectoryError: If the resolved parent is not a directory.
            ValueError: If the name is empty, reserved, or contains a path
                separator.
            FileExistsError: If the destination already exists.
        """
        directory = directory.expanduser().resolve()
        name = self._validate_name(name)
        if not directory.is_dir():
            raise NotADirectoryError(directory)

        path = directory / name
        path.mkdir()
        return path

    @staticmethod
    def _validate_name(name: str) -> str:
        """Trim and validate a folder name as one path component.

        Raises:
            ValueError: If the trimmed value is empty, ``.`` or ``..``, or
                contains either platform path separator.
        """
        name = name.strip()
        if not name or name in {".", ".."} or "/" in name or "\\" in name:
            raise ValueError("Enter a valid folder name")
        return name
