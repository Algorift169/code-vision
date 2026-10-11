"""Read and persist the user's automatic-save preference."""

from __future__ import annotations

import os
from pathlib import Path


class AutoSaveSettings:
    """Store whether automatic saving is enabled for the current user.

    The setting is represented by a small text file under the configured
    CodeVision directory, or at an explicitly supplied path.
    """

    def __init__(self, state_path: str | Path | None = None) -> None:
        """Choose the state file path without reading or writing it.

        By default, the XDG config directory is used when configured;
        otherwise the path is placed under ``~/.config/codevision``.

        Args:
            state_path: Optional path overriding the default setting file.
        """
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
        """Return whether the setting file contains the enabled marker.

        Only the stripped text ``1`` means enabled. If reading the file fails,
        the preference is treated as disabled.
        """
        try:
            return self._state_path.read_text(encoding="utf-8").strip() == "1"
        except OSError:
            return False

    def set_enabled(self, enabled: bool) -> None:
        """Persist the enabled state, creating its parent directory as needed.

        The file contains ``1`` when enabled and ``0`` otherwise. Filesystem
        errors are ignored, so callers should not interpret this method's
        return as confirmation that persistence succeeded.
        """
        try:
            self._state_path.parent.mkdir(parents=True, exist_ok=True)
            self._state_path.write_text("1" if enabled else "0", encoding="utf-8")
        except OSError:
            pass
