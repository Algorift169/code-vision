from pathlib import Path

import pytest

from codevision.services.file_operations import FileOperationService
from codevision.ui.widgets.menu_actions import delete, rename
from codevision.ui.widgets.menu_context import MenuContext


def test_rename_handles_files_folders_and_spaces(tmp_path: Path) -> None:
    service = FileOperationService()
    source_file = tmp_path / "old name.txt"
    source_file.write_text("contents", encoding="utf-8")
    source_folder = tmp_path / "old folder"
    source_folder.mkdir()

    renamed_file = service.rename(source_file, "new name.txt")
    renamed_folder = service.rename(source_folder, "new folder")

    assert renamed_file.read_text(encoding="utf-8") == "contents"
    assert renamed_folder.is_dir()


def test_rename_rejects_existing_and_nested_names(tmp_path: Path) -> None:
    service = FileOperationService()
    source = tmp_path / "source.txt"
    target = tmp_path / "target.txt"
    source.touch()
    target.touch()

    with pytest.raises(FileExistsError):
        service.rename(source, target.name)
    with pytest.raises(ValueError):
        service.rename(source, "../outside.txt")


def test_delete_removes_files_folders_and_only_the_symlink(tmp_path: Path) -> None:
    service = FileOperationService()
    target = tmp_path / "target"
    target.mkdir()
    (target / "nested.txt").touch()
    link = tmp_path / "target-link"
    link.symlink_to(target, target_is_directory=True)

    service.delete(link)
    assert target.is_dir()
    service.delete(target)
    assert not target.exists()

    file_path = tmp_path / "file.txt"
    file_path.touch()
    service.delete(file_path)
    assert not file_path.exists()


def test_menu_actions_only_allow_items_inside_project_root(tmp_path: Path) -> None:
    root = tmp_path / "project"
    child = root / "file.txt"
    outside = tmp_path / "outside.txt"
    root.mkdir()
    child.touch()
    outside.touch()

    root_context = MenuContext(widget=None, kind="explorer", path=root, project_root=root)
    child_context = MenuContext(
        widget=None, kind="explorer", path=child, project_root=root
    )
    outside_context = MenuContext(
        widget=None, kind="explorer", path=outside, project_root=root
    )

    assert not delete.is_enabled(root_context)
    assert not rename.is_enabled(root_context)
    assert delete.is_enabled(child_context)
    assert rename.is_enabled(child_context)
    assert not delete.is_enabled(outside_context)
    assert not rename.is_enabled(outside_context)
