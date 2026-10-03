from pathlib import Path

from codevision.services.file_search import FileSearchConfig, FileSearchService


def _names(service: FileSearchService, root: Path, query: str) -> list[str]:
    return [result.relative_path.as_posix() for result in service.search(root, query).entries]


def test_search_prioritizes_files_folders_then_hidden(tmp_path: Path) -> None:
    (tmp_path / "main.c").touch()
    (tmp_path / "main.cpp").touch()
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.c").touch()
    (tmp_path / "main").mkdir()
    (tmp_path / ".main-config").touch()

    results = _names(FileSearchService(), tmp_path, "main")

    assert results == ["main.c", "src/main.c", "main.cpp", "main", ".main-config"]


def test_exact_name_beats_partial_names_and_is_case_insensitive(tmp_path: Path) -> None:
    for filename in ("main.c", "main.cpp", "main.c.bak"):
        (tmp_path / filename).touch()
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.c").touch()

    assert _names(FileSearchService(), tmp_path, "MAIN.C") == [
        "main.c",
        "src/main.c",
        "main.cpp",
        "main.c.bak",
    ]


def test_fuzzy_match_is_supported_but_ignored_directories_are_not_traversed(
    tmp_path: Path,
) -> None:
    (tmp_path / "main_window.py").touch()
    ignored = tmp_path / "node_modules"
    ignored.mkdir()
    (ignored / "main_window.js").touch()

    results = FileSearchService().search(tmp_path, "mwn")

    assert [result.name for result in results.entries] == ["main_window.py"]
    assert results.entries[0].match_type == "fuzzy"


def test_empty_query_does_not_traverse_and_result_limit_is_reported(tmp_path: Path) -> None:
    for index in range(3):
        (tmp_path / f"file{index}.c").touch()

    service = FileSearchService(FileSearchConfig(result_limit=2))
    assert service.search(tmp_path, "").total_count == 0
    results = service.search(tmp_path, "file")
    assert len(results.entries) == 2
    assert results.total_count == 3
