from __future__ import annotations

import shutil
from pathlib import Path


class FileOperationService:
    """Filesystem operations for project Explorer items."""

    def delete(self, path: Path) -> None:
        path = path.expanduser()
        if not path.exists() and not path.is_symlink():
            raise FileNotFoundError(path)
        if path.is_symlink() or not path.is_dir():
            path.unlink()
        else:
            shutil.rmtree(path)

    def rename(self, path: Path, name: str) -> Path:
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
        name = name.strip()
        if not name or name in {".", ".."} or "/" in name or "\\" in name:
            raise ValueError("Enter a valid name")
        return name
