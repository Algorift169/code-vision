from __future__ import annotations

import os
from pathlib import Path


class AutoSaveSettings:
    """Persist whether automatic saving is enabled for this user."""

    def __init__(self, state_path: str | Path | None = None) -> None:
        config_dir = Path(
            os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")
        )
        self._state_path = (
            Path(state_path)
            if state_path is not None
            else config_dir / "codevision" / "auto-save"
        )

    @property
    def enabled(self) -> bool:
        try:
            return self._state_path.read_text(encoding="utf-8").strip() == "1"
        except OSError:
            return False

    def set_enabled(self, enabled: bool) -> None:
        try:
            self._state_path.parent.mkdir(parents=True, exist_ok=True)
            self._state_path.write_text("1" if enabled else "0", encoding="utf-8")
        except OSError:
            pass
