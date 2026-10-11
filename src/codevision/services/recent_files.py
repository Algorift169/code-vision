"""Persist a bounded, deduplicated list of recently used files."""

from __future__ import annotations

import json
from pathlib import Path


class RecentFilesService:
    """Track recent file paths in most-recent-first order.

    Each operation reloads the persisted list so service instances observe
    recent changes on disk. Paths are normalized and duplicates are removed;
    the list is capped to the configured maximum number of items.
    """

    def __init__(self, max_items: int = 10, state_path: str | Path | None = None) -> None:
        """Initialize recent-file storage and load the current list.

        The item limit is clamped to at least one. Unless overridden, state is
        stored in the user's ``~/.config/codevision`` directory.

        Args:
            max_items: Maximum number of paths retained in the list.
            state_path: Optional JSON file path used for persistence.
        """
        self._max_items = max(1, max_items)
        self._state_path = Path(state_path) if state_path is not None else (
            Path.home() / ".config" / "codevision" / "recent-files.json"
        )
        self._items: list[Path] = self._load()

    def add(self, path: str | Path) -> list[Path]:
        """Move a path to the front and persist the bounded recent list.

        The supplied path is expanded and resolved. Any prior occurrence is
        removed before inserting it as most recent, then the list is truncated
        to the configured limit.

        Args:
            path: File path to mark as recently used.

        Returns:
            A copy of the updated most-recent-first path list.
        """
        self._items = self._load()
        resolved = Path(path).expanduser().resolve()
        cleaned = [item for item in self._items if item != resolved]
        cleaned.insert(0, resolved)
        self._items = cleaned[: self._max_items]
        self._save()
        return list(self._items)

    def get_recent(self) -> list[Path]:
        """Return existing files in the persisted recent list.

        Missing paths and directories are filtered out. The cleaned list is
        written back before a copy is returned.
        """
        self._items = self._load()
        self._items = [path for path in self._items if path.is_file()]
        self._save()
        return list(self._items)

    def clear(self) -> None:
        """Remove all recent paths from memory and persisted storage."""
        self._items.clear()
        self._save()

    def _load(self) -> list[Path]:
        """Read, normalize, deduplicate, and limit persisted recent paths.

        Missing files, malformed JSON, unexpected data types, and filesystem
        or conversion errors produce an empty list.
        """
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
        """Write the current path list as JSON, creating its parent directory.

        Filesystem errors are ignored; callers therefore receive no indication
        that persistence failed.
        """
        try:
            self._state_path.parent.mkdir(parents=True, exist_ok=True)
            payload = [str(path) for path in self._items]
            self._state_path.write_text(json.dumps(payload), encoding="utf-8")
        except OSError:
            pass
