from pathlib import Path

import pytest

from codevision.services.folder_browser import FolderBrowserService


def test_list_entries_sorts_directories_before_files(tmp_path: Path) -> None:
    (tmp_path / "zeta.txt").touch()
    (tmp_path / "Beta").mkdir()
    (tmp_path / "alpha").mkdir()

    entries = FolderBrowserService().list_entries(tmp_path, show_hidden=False)

    assert [entry.name for entry in entries] == ["alpha", "Beta", "zeta.txt"]
    assert [entry.is_directory for entry in entries] == [True, True, False]


def test_list_entries_rejects_a_file(tmp_path: Path) -> None:
    file_path = tmp_path / "file.txt"
    file_path.touch()

    with pytest.raises(NotADirectoryError):
        FolderBrowserService().list_entries(file_path, show_hidden=False)


def test_list_entries_hides_dotfiles_when_disabled(tmp_path: Path) -> None:
    (tmp_path / ".hidden-file").touch()
    (tmp_path / "visible-file").touch()
    (tmp_path / ".hidden-folder").mkdir()
    (tmp_path / "visible-folder").mkdir()

    entries = FolderBrowserService().list_entries(tmp_path, show_hidden=False)

    assert [entry.name for entry in entries] == ["visible-folder", "visible-file"]


def test_list_entries_can_include_dotfiles_when_enabled(tmp_path: Path) -> None:
    (tmp_path / ".hidden-file").touch()
    (tmp_path / "visible-file").touch()

    entries = FolderBrowserService().list_entries(tmp_path, show_hidden=True)

    assert [entry.name for entry in entries] == [".hidden-file", "visible-file"]


def test_parent_directory_returns_none_at_filesystem_root() -> None:
    service = FolderBrowserService()
    root = Path(Path.cwd().anchor)

    assert service.parent_directory(root) is None
