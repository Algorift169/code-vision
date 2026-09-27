from __future__ import annotations

from pathlib import Path


class SaveService:
    """Persist editor text to a file using UTF-8 encoding."""

    def save_file(self, path: Path, content: str) -> Path:
        path = Path(path).expanduser()
        path.write_text(content, encoding="utf-8")
        return path
