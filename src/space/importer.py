from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio


_VIDEO_EXTENSIONS = {
    ".3g2",
    ".3gp",
    ".avi",
    ".flv",
    ".m2ts",
    ".m4v",
    ".mkv",
    ".mov",
    ".mp4",
    ".mpeg",
    ".mpg",
    ".mts",
    ".ogv",
    ".ts",
    ".vob",
    ".webm",
    ".wmv",
}


@dataclass(frozen=True)
class ImportedFile:
    path: Path
    content_type: str
    mime_type: str


def describe_file(path: Path) -> ImportedFile:
    path = path.expanduser().resolve(strict=True)
    if not path.is_file():
        raise ValueError(f"Not a file: {path.name}")

    with path.open("rb") as file:
        header = file.read(4096)

    content_type, _uncertain = Gio.content_type_guess(str(path), header)
    mime_type = Gio.content_type_get_mime_type(content_type) or (
        "application/octet-stream"
    )
    if mime_type.startswith("video/") or path.suffix.lower() in _VIDEO_EXTENSIONS:
        raise ValueError(f"Video files cannot be imported: {path.name}")

    return ImportedFile(path, content_type, mime_type)
