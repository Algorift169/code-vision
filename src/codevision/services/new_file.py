from __future__ import annotations

from pathlib import Path


class NewFileService:
    """Create a new empty file within a project directory."""

    def create(self, directory: Path, name: str) -> Path:
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
        name = name.strip()
        if not name or name in {".", ".."} or "/" in name or "\\" in name:
            raise ValueError("Enter a valid file name")
        return name
