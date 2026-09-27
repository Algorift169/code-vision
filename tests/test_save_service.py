from pathlib import Path

from codevision.services.save import SaveService


def test_save_file_creates_or_overwrites_utf8_file(tmp_path: Path) -> None:
    path = tmp_path / "notes.txt"
    service = SaveService()

    service.save_file(path, "first line\n")
    saved_path = service.save_file(path, "Updated: café\n")

    assert saved_path == path
    assert path.read_text(encoding="utf-8") == "Updated: café\n"
