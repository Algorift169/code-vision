"""Perform delete and rename operations on project filesystem entries."""

from __future__ import annotations

import shutil
from pathlib import Path


class FileOperationService:
    """Delete and rename files, directories, and symbolic links.

    Paths are expanded before operations. Symbolic links are treated as links
    themselves rather than followed for deletion.
    """

    def delete(self, path: Path) -> None:
        """Remove a file, symbolic link, or directory tree.

        A symbolic link is unlinked even when it points to a directory;
        ordinary directories are recursively removed. A missing path raises
        ``FileNotFoundError`` instead of being treated as already deleted.

        Args:
            path: Filesystem entry to remove.

        Raises:
            FileNotFoundError: If the entry does not exist and is not a
                symbolic link.
            OSError: If the underlying filesystem removal fails.
        """
        path = path.expanduser()
        if not path.exists() and not path.is_symlink():
            raise FileNotFoundError(path)
        if path.is_symlink() or not path.is_dir():
            path.unlink()
        else:
            shutil.rmtree(path)

    def rename(self, path: Path, name: str) -> Path:
        """Rename an existing filesystem entry within its current parent.

        The new name is trimmed and validated as a single path component.
        Requesting the current path is a no-op; an existing destination is
        rejected rather than replaced.

        Args:
            path: Existing file, directory, or symbolic link to rename.
            name: New base name for the entry.

        Returns:
            The unchanged path for a no-op, or the path returned by rename.

        Raises:
            FileNotFoundError: If the source does not exist.
            ValueError: If the new name is empty, reserved, or contains a
                path separator.
            FileExistsError: If a different destination already exists.
            OSError: If the underlying rename operation fails.
        """
        path = path.expanduser()
        if not path.exists() and not path.is_symlink():
            raise FileNotFoundError(path)

        name = self._validate_name(name)
        destination = path.with_name(name)
        if destination == path:
            return path
        if destination.exists() or destination.is_symlink():
            raise FileExistsError(destination)
        return path.rename(destination)

    @staticmethod
    def _validate_name(name: str) -> str:
        """Trim and validate a name as one non-reserved path component.

        Raises:
            ValueError: If the trimmed name is empty, ``.`` or ``..``, or
                contains either path separator.
        """
        name = name.strip()
        if not name or name in {".", ".."} or "/" in name or "\\" in name:
            raise ValueError("Enter a valid name")
        return name
