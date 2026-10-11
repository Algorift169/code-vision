"""Persist editor buffer contents to filesystem paths."""

from __future__ import annotations

from pathlib import Path


class SaveService:
    """Write editor text to a destination file using UTF-8 encoding.

    This small service centralizes the filesystem write used by editor save
    operations and returns the expanded destination path to the caller.
    """

    def save_file(self, path: Path, content: str) -> Path:
        """Write ``content`` to ``path`` and return the expanded path.

        Parent directories are not created automatically. Filesystem errors
        from ``Path.write_text`` propagate to the caller.

        Args:
            path: Destination file path, potentially containing ``~``.
            content: Complete text content to write using UTF-8 encoding.

        Returns:
            The destination path after user-home expansion.
        """
        path = Path(path).expanduser()
        path.write_text(content, encoding="utf-8")
        return path
