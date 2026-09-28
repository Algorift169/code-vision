from __future__ import annotations

from pathlib import Path


class NewFolderService:
    """Create a new directory within a project directory."""

    def create(self, directory: Path, name: str) -> Path:
        directory = directory.expanduser().resolve()
        name = self._validate_name(name)
        if not directory.is_dir():
            raise NotADirectoryError(directory)

        path = directory / name
        path.mkdir()
        return path

    @staticmethod
    def _validate_name(name: str) -> str:
        name = name.strip()
        if not name or name in {".", ".."} or "/" in name or "\\" in name:
            raise ValueError("Enter a valid folder name")
        return name
