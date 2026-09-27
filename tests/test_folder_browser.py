from pathlib import Path

import pytest

from codevision.services.folder_browser import FolderBrowserService


def test_list_entries_sorts_directories_before_files(tmp_path: Path) -> None:
    (tmp_path / "zeta.txt").touch()
    (tmp_path / "Beta").mkdir()
    (tmp_path / "alpha").mkdir()

    entries = FolderBrowserService().list_entries(tmp_path)

    assert [entry.name for entry in entries] == ["alpha", "Beta", "zeta.txt"]
    assert [entry.is_directory for entry in entries] == [True, True, False]


def test_list_entries_rejects_a_file(tmp_path: Path) -> None:
    file_path = tmp_path / "file.txt"
    file_path.touch()

    with pytest.raises(NotADirectoryError):
        FolderBrowserService().list_entries(file_path)


def test_parent_directory_returns_none_at_filesystem_root() -> None:
    service = FolderBrowserService()
    root = Path(Path.cwd().anchor)

    assert service.parent_directory(root) is None
