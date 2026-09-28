from pathlib import Path

from codevision.ui.widgets.menu_actions.copy_full_path import full_path
from codevision.ui.widgets.menu_actions.copy_relative_path import relative_path
from codevision.ui.widgets.menu_actions.paste import copy_files_to_directory
from codevision.ui.widgets.menu_context import MenuContext


def test_path_copy_actions_resolve_paths_with_spaces(tmp_path: Path) -> None:
    root = tmp_path / "project with spaces"
    file_path = root / "source files" / "main file.py"
    file_path.parent.mkdir(parents=True)
    file_path.touch()
    context = MenuContext(
        widget=None,
        kind="explorer",
        path=file_path,
        project_root=root,
    )

    assert full_path(context) == file_path.resolve()
    assert relative_path(context) == Path("source files/main file.py")


def test_relative_path_rejects_paths_outside_project(tmp_path: Path) -> None:
    root = tmp_path / "project"
    outside = tmp_path / "outside.py"
    root.mkdir()
    outside.touch()
    context = MenuContext(
        widget=None,
        kind="explorer",
        path=outside,
        project_root=root,
    )

    assert relative_path(context) is None


def test_file_paste_copies_files_and_directories_with_spaces(tmp_path: Path) -> None:
    source_root = tmp_path / "source files"
    source_root.mkdir()
    source_file = source_root / "main file.py"
    source_file.write_text("print('hello')", encoding="utf-8")
    source_folder = source_root / "folder with spaces"
    source_folder.mkdir()
    (source_folder / "nested.txt").write_text("nested", encoding="utf-8")
    destination = tmp_path / "destination"
    destination.mkdir()

    copied = copy_files_to_directory([source_file, source_folder], destination)

    assert copied == [destination / source_file.name, destination / source_folder.name]
    assert copied[0].read_text(encoding="utf-8") == "print('hello')"
    assert (copied[1] / "nested.txt").read_text(encoding="utf-8") == "nested"
