from pathlib import Path

import pytest

from codevision.ui.theme import THEMES, ThemeManager


STYLES_DIRECTORY = Path(__file__).resolve().parents[1] / "resources" / "styles"


def test_all_themes_have_a_stylesheet() -> None:
    assert len(THEMES) == 10
    assert all((STYLES_DIRECTORY / theme.stylesheet).is_file() for theme in THEMES)


def test_theme_choice_is_applied_and_persisted(tmp_path: Path) -> None:
    preferences_file = tmp_path / "config" / "theme"
    manager = ThemeManager(STYLES_DIRECTORY, preferences_file)

    manager.apply("paper-ink")

    assert manager.current_theme == "paper-ink"
    assert preferences_file.read_text(encoding="utf-8") == "paper-ink"
    assert ThemeManager(STYLES_DIRECTORY, preferences_file).current_theme == "paper-ink"


def test_unknown_theme_is_rejected(tmp_path: Path) -> None:
    manager = ThemeManager(STYLES_DIRECTORY, tmp_path / "theme")

    with pytest.raises(ValueError, match="Unknown theme"):
        manager.apply("not-a-theme")
