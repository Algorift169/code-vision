from __future__ import annotations

from codevision.editor.tab import EditorTabs
from codevision.services.kong_browser import KongBrowserService
from codevision.ui.widgets.menu import ContextMenu
from codevision.ui.widgets.menu_context import MenuContext


def test_kong_browser_service_normalizes_and_splits_url_targets() -> None:
    service = KongBrowserService(search_engine="https://duckduckgo.com/?q={query}")

    assert service.normalize_url("https://example.com") == "https://example.com"
    assert service.normalize_url("example.com") == "https://example.com"
    assert service.normalize_url("github.com") == "https://github.com"
    assert service.normalize_url("hello world") == "https://duckduckgo.com/?q=hello+world"
    assert service.is_valid_url("https://example.com")
    assert not service.is_valid_url("not a url")


def test_kong_browser_service_tracks_navigation_state() -> None:
    service = KongBrowserService()
    service.load_url("https://example.com")

    assert service.current_url == "https://example.com"
    assert service.page_title == "Kong Browser"
    assert service.loading is True

    service.set_loaded()
    assert service.loading is False
    service.set_title("Example Domain")
    assert service.page_title == "Example Domain"


def test_context_menu_exposes_kong_action() -> None:
    actions = {item[0] for item in ContextMenu._ACTIONS}
    assert "kong-browser" in actions


def test_editor_tabs_reuse_existing_kong_browser() -> None:
    tabs = EditorTabs()
    first = tabs.open_kong_browser()
    second = tabs.open_kong_browser()

    assert first is second
    assert tabs.get_n_pages() == 1


def test_editor_tabs_can_open_a_new_kong_browser_tab() -> None:
    tabs = EditorTabs()
    first = tabs.open_kong_browser()

    first.new_tab()
    second = tabs.active_page

    assert second is not first
    assert tabs.get_n_pages() == 2


def test_menu_context_detects_selected_url() -> None:
    context = MenuContext(widget=None, kind="editor", selected_text="https://example.com")
    assert KongBrowserService.is_selected_url(context.selected_text)
    assert KongBrowserService.is_selected_url("https://example.com/path")
    assert not KongBrowserService.is_selected_url("just some words")


def test_kong_browser_theme_updates_without_restart() -> None:
    browser = KongBrowserService()
    browser.set_theme("obsidian-forge")
    assert browser.theme_id == "obsidian-forge"

    browser.set_theme("crimson-core")
    assert browser.theme_id == "crimson-core"


def test_kong_browser_can_shutdown_without_webkit() -> None:
    service = KongBrowserService()
    service.load_url("https://example.com")
    service.stop()
    service.destroy()
    assert service.destroyed is True
