from pathlib import Path

import pytest

from codevision.services.folder_browser import FolderBrowserService
from codevision.services.new_file import NewFileService
from codevision.services.new_folder import NewFolderService


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


def test_new_file_service_creates_file_in_selected_directory(tmp_path: Path) -> None:
    nested = tmp_path / "nested"
    nested.mkdir()

    created = NewFileService().create(nested, "notes.txt")

    assert created == nested / "notes.txt"
    assert created.is_file()
    assert created.read_text(encoding="utf-8") == ""


def test_new_file_service_rejects_existing_or_nested_names(tmp_path: Path) -> None:
    service = NewFileService()
    service.create(tmp_path, "notes.txt")

    with pytest.raises(FileExistsError):
        service.create(tmp_path, "notes.txt")
    with pytest.raises(ValueError):
        service.create(tmp_path, "../outside.txt")


def test_new_folder_service_creates_folder_and_rejects_duplicates(
    tmp_path: Path,
) -> None:
    service = NewFolderService()

    created = service.create(tmp_path, "src")

    assert created == tmp_path / "src"
    assert created.is_dir()
    with pytest.raises(FileExistsError):
        service.create(tmp_path, "src")
    with pytest.raises(ValueError):
        service.create(tmp_path, "../outside")
