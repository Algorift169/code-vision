"""Create new files in project directories with validated single-component names."""

from __future__ import annotations

from pathlib import Path


class NewFileService:
    """Create empty files within existing project directories.

    Names are restricted to one path component, and exclusive file creation
    prevents an existing file from being overwritten.
    """

    def create(self, directory: Path, name: str) -> Path:
        """Create an empty file and return its resolved parent-based path.

        The directory is expanded and resolved before it is checked. The
        requested name is stripped and validated, then opened in exclusive
        creation mode so an existing destination raises ``FileExistsError``.

        Args:
            directory: Existing directory in which to create the file.
            name: File name without directory separators.

        Returns:
            The new file path beneath the resolved directory.

        Raises:
            NotADirectoryError: If the resolved parent is not a directory.
            ValueError: If the name is empty, reserved, or contains a path
                separator.
            FileExistsError: If a file with the requested name already exists.
        """
        directory = directory.expanduser().resolve()
        name = self._validate_name(name)
        if not directory.is_dir():
            raise NotADirectoryError(directory)

        path = directory / name
        with path.open("x", encoding="utf-8"):
            pass
        return path

    @staticmethod
    def _validate_name(name: str) -> str:
        """Trim and validate a file name as one non-reserved path component.

        Raises:
            ValueError: If the trimmed value is empty, ``.`` or ``..``, or
                contains either platform path separator.
        """
        name = name.strip()
        if not name or name in {".", ".."} or "/" in name or "\\" in name:
            raise ValueError("Enter a valid file name")
        return name
