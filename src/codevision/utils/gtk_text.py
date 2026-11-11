from __future__ import annotations

import os
from pathlib import Path


def gtk_safe_text(value: str) -> str:
    return value.encode("utf-8", errors="backslashreplace").decode("utf-8")


def path_to_gtk_token(path: Path) -> str:
    return f"fs:{os.fsencode(path).hex()}"


def path_from_gtk_token(value: str) -> Path:
    if value.startswith("fs:"):
        return Path(os.fsdecode(bytes.fromhex(value[3:])))
    return Path(value)