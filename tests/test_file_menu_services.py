from pathlib import Path

from codevision.services.auto_save import AutoSaveSettings
from codevision.services.recent_files import RecentFilesService


def test_recent_files_are_deduplicated_bounded_and_persisted(tmp_path: Path) -> None:
    state_path = tmp_path / "config" / "recent.json"
    first = tmp_path / "first file.c"
    second = tmp_path / "café (parser).cpp"
    third = tmp_path / "third.txt"
    for path in (first, second, third):
        path.touch()

    service = RecentFilesService(max_items=2, state_path=state_path)
    observer = RecentFilesService(max_items=2, state_path=state_path)
    service.add(first)
    assert observer.get_recent() == [first.resolve()]
    service.add(second)
    assert service.add(first) == [first.resolve(), second.resolve()]
    assert service.add(third) == [third.resolve(), first.resolve()]

    reopened = RecentFilesService(max_items=2, state_path=state_path)
    assert reopened.get_recent() == [third.resolve(), first.resolve()]
    third.unlink()
    assert reopened.get_recent() == [first.resolve()]


def test_auto_save_setting_is_persisted(tmp_path: Path) -> None:
    state_path = tmp_path / "config" / "auto-save"
    settings = AutoSaveSettings(state_path)

    assert not settings.enabled
    settings.set_enabled(True)
    assert AutoSaveSettings(state_path).enabled
    settings.set_enabled(False)
    assert not AutoSaveSettings(state_path).enabled
