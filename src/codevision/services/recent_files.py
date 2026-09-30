from __future__ import annotations

import json
from pathlib import Path


class RecentFilesService:
    """Tracks recently opened or saved files and keeps a compact deduplicated list."""

    def __init__(self, max_items: int = 10, state_path: str | Path | None = None) -> None:
        self._max_items = max(1, max_items)
        self._state_path = Path(state_path) if state_path is not None else (
            Path.home() / ".config" / "codevision" / "recent-files.json"
        )
        self._items: list[Path] = self._load()

    def add(self, path: str | Path) -> list[Path]:
        self._items = self._load()
        resolved = Path(path).expanduser().resolve()
        cleaned = [item for item in self._items if item != resolved]
        cleaned.insert(0, resolved)
        self._items = cleaned[: self._max_items]
        self._save()
        return list(self._items)

    def get_recent(self) -> list[Path]:
        self._items = self._load()
        self._items = [path for path in self._items if path.is_file()]
        self._save()
        return list(self._items)

    def clear(self) -> None:
        self._items.clear()
        self._save()

    def _load(self) -> list[Path]:
        try:
            if not self._state_path.exists():
                return []
            data = json.loads(self._state_path.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                return []
            items = dict.fromkeys(
                Path(item).expanduser().resolve()
                for item in data
                if isinstance(item, str) and item
            )
            return list(items)[: self._max_items]
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            return []

    def _save(self) -> None:
        try:
            self._state_path.parent.mkdir(parents=True, exist_ok=True)
            payload = [str(path) for path in self._items]
            self._state_path.write_text(json.dumps(payload), encoding="utf-8")
        except OSError:
            pass
