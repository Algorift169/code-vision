from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, Gtk

# WebKitGTK 4.1 is the GTK3 binding and cannot be loaded in this GTK4
# process. WebKitGTK 6.0 (or 5.0 on older distributions) is the GTK4 API.
WebKit = None
WEBKIT_ERROR = "WebKitGTK 6.0 (GTK4) is not available"
for _webkit_namespace, _webkit_version in (("WebKit", "6.0"), ("WebKit", "5.0")):
    try:
        gi.require_version(_webkit_namespace, _webkit_version)
        WebKit = getattr(__import__("gi.repository", fromlist=[_webkit_namespace]), _webkit_namespace)
        WEBKIT_ERROR = ""
        break
    except (ImportError, ValueError):
        continue

from ..services.kong_browser import KongBrowserService


class KongBrowser(Gtk.Box):
    """Embedded browser tab that preserves CodeVision's editor-tab model."""

    def __init__(
        self,
        initial_url: str | None = None,
        *,
        on_close: Callable[[], None] | None = None,
        on_new_tab: Callable[[], None] | None = None,
    ) -> None:
        self._headless = Gdk.Display.get_default() is None
        if self._headless:
            self._on_close = on_close
            self._on_new_tab = on_new_tab
            self.service = KongBrowserService(initial_url)
            self._stack = _HeadlessStack()
            self._toolbar = _HeadlessToolbar()
            self.back_button = _HeadlessButton()
            self.forward_button = _HeadlessButton()
            self.reload_button = _HeadlessButton()
            self.new_tab_button = _HeadlessButton()
            self.url_entry = _HeadlessEntry(initial_url or "")
            self._error_url = _HeadlessLabel()
            self._start_page = _HeadlessLayout()
            self._error_page = _HeadlessLayout()
            self._browser = None
            self.service.current_url = self.service.normalize_url(initial_url) if initial_url else ""
            self._apply_state()
            return

        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_name("kong-browser")
        self.add_css_class("kong-browser")
        self.set_hexpand(True)
        self.set_vexpand(True)
        self._on_close = on_close
        self._on_new_tab = on_new_tab
        self.service = KongBrowserService(initial_url)
        self._stack = Gtk.Stack()
        self._stack.set_hexpand(True)
        self._stack.set_vexpand(True)
        self._build_toolbar()
        self._build_start_page()
        self._build_error_page()
        self._build_webview()
        self.append(self._toolbar)
        self.append(self._stack)
        self._apply_state()

    def _build_toolbar(self) -> None:
        self._toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._toolbar.add_css_class("kong-toolbar")
        self._toolbar.set_margin_top(8)
        self._toolbar.set_margin_bottom(8)
        self._toolbar.set_margin_start(12)
        self._toolbar.set_margin_end(12)

        self.back_button = Gtk.Button(label="◀")
        self.back_button.add_css_class("kong-navigation-button")
        self.back_button.set_tooltip_text("Back")
        self.back_button.connect("clicked", lambda *_args: self.go_back())

        self.forward_button = Gtk.Button(label="▶")
        self.forward_button.add_css_class("kong-navigation-button")
        self.forward_button.set_tooltip_text("Forward")
        self.forward_button.connect("clicked", lambda *_args: self.go_forward())

        self.reload_button = Gtk.Button(label="↻")
        self.reload_button.add_css_class("kong-navigation-button")
        self.reload_button.set_tooltip_text("Reload")
        self.reload_button.connect("clicked", lambda *_args: self.reload())

        self.new_tab_button = Gtk.Button(label="+")
        self.new_tab_button.add_css_class("kong-navigation-button")
        self.new_tab_button.set_tooltip_text("New browser tab")
        self.new_tab_button.connect("clicked", lambda *_args: self.new_tab())

        self.url_entry = Gtk.Entry()
        self.url_entry.set_hexpand(True)
        self.url_entry.set_placeholder_text("Search or enter URL")
        self.url_entry.add_css_class("kong-url-entry")
        self.url_entry.connect("activate", self._on_url_activated)
        self.url_entry.connect(
            "notify::has-focus",
            lambda *_args: self._select_url() if self.url_entry.has_focus() else None,
        )

        self._toolbar.append(self.back_button)
        self._toolbar.append(self.forward_button)
        self._toolbar.append(self.reload_button)
        self._toolbar.append(self.url_entry)
        self._toolbar.append(self.new_tab_button)

    def _build_start_page(self) -> None:
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        page.add_css_class("kong-start-page")
        page.set_hexpand(True)
        page.set_vexpand(True)
        page.set_valign(Gtk.Align.CENTER)
        page.set_halign(Gtk.Align.CENTER)
        title = Gtk.Label(label="KONG")
        title.add_css_class("kong-title")
        subtitle = Gtk.Label(label="CodeVision Integrated Browser")
        subtitle.add_css_class("kong-subtitle")
        hint = Gtk.Label(label="Search the web or enter a URL above")
        hint.add_css_class("kong-hint")
        page.append(title)
        page.append(subtitle)
        page.append(hint)
        self._start_page = page
        self._stack.add_named(page, "start")

    def _build_error_page(self) -> None:
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        page.add_css_class("kong-error-page")
        page.set_hexpand(True)
        page.set_vexpand(True)
        page.set_valign(Gtk.Align.CENTER)
        page.set_halign(Gtk.Align.CENTER)
        title = Gtk.Label(label="Unable to load this page")
        title.add_css_class("kong-error-title")
        url = Gtk.Label(label="")
        url.add_css_class("kong-error-url")
        retry = Gtk.Button(label="Try Again")
        retry.add_css_class("kong-error-button")
        retry.connect("clicked", lambda *_args: self.reload())
        page.append(title)
        page.append(url)
        page.append(retry)
        self._error_url = url
        self._error_page = page
        self._stack.add_named(page, "error")

    def _build_webview(self) -> None:
        if WebKit is None:
            self._webview = None
            self._stack.add_named(Gtk.Label(label=WEBKIT_ERROR), "browser")
            self._stack.set_visible_child_name("start")
            return

        self._browser = WebKit.WebView()
        self._browser.set_hexpand(True)
        self._browser.set_vexpand(True)
        self._browser.add_css_class("kong-webview")
        self._browser.connect("load-changed", self._on_load_changed)
        self._browser.connect("notify::title", self._on_title_changed)
        self._stack.add_named(self._browser, "browser")
        self._stack.set_visible_child_name("start")

    def _on_url_activated(self, _entry: Gtk.Entry) -> None:
        self.load_url(self.url_entry.get_text())

    def _on_load_changed(self, _webview: WebKit.WebView, event: object) -> None:
        if event == WebKit.LoadEvent.STARTED:
            self.service.loading = True
        elif event in (WebKit.LoadEvent.FINISHED, WebKit.LoadEvent.FAILED):
            self.service.set_loaded()
            if event == WebKit.LoadEvent.FAILED:
                self._show_error(self.service.current_url)
        self._apply_state()

    def _on_title_changed(self, _webview: WebKit.WebView, _param) -> None:
        title = self._browser.get_title()
        if title:
            self.service.set_title(title)
        self._apply_state()

    def _select_url(self) -> None:
        if self.url_entry.get_text():
            self.url_entry.select_region(0, -1)

    def _show_error(self, url: str | None) -> None:
        if self._error_url is not None:
            self._error_url.set_text(url or "about:blank")
        self._stack.set_visible_child_name("error")

    def _apply_state(self) -> None:
        if self.service.current_url and self._stack.get_visible_child_name() == "start":
            self._stack.set_visible_child_name("browser")
        self.url_entry.set_text(self.service.current_url)
        self.back_button.set_sensitive(self.service.history_index > 0)
        self.forward_button.set_sensitive(
            self.service.history_index < len(self.service.history) - 1
        )
        self.reload_button.set_label("×" if self.service.loading else "↻")
        self.reload_button.set_tooltip_text("Stop loading" if self.service.loading else "Reload")

    def load_url(self, value: str | None) -> None:
        url = self.service.normalize_url(value)
        if not url:
            self._stack.set_visible_child_name("start")
            return
        self.service.load_url(url)
        self.url_entry.set_text(self.service.current_url)
        if WebKit is not None and self._browser is not None:
            self._browser.load_uri(self.service.current_url)
            self._stack.set_visible_child_name("browser")
        else:
            self._stack.set_visible_child_name("start")
        self._apply_state()

    def go_back(self) -> None:
        if not self.service.history or self.service.history_index <= 0:
            return
        self.service.go_back()
        if WebKit is not None and self._browser is not None:
            self._browser.load_uri(self.service.current_url)
        self._apply_state()

    def go_forward(self) -> None:
        if not self.service.history or self.service.history_index >= len(self.service.history) - 1:
            return
        self.service.go_forward()
        if WebKit is not None and self._browser is not None:
            self._browser.load_uri(self.service.current_url)
        self._apply_state()

    def reload(self) -> None:
        if self.service.loading:
            self.service.stop()
            if WebKit is not None and self._browser is not None:
                self._browser.stop_loading()
            self._apply_state()
            return
        self.service.reload()
        if WebKit is not None and self._browser is not None:
            self._browser.reload()
        self._apply_state()

    def stop(self) -> None:
        self.service.stop()
        if WebKit is not None and self._browser is not None:
            self._browser.stop_loading()
        self._apply_state()

    def focus_url_bar(self) -> None:
        self.url_entry.grab_focus()
        self.url_entry.select_region(0, -1)

    def new_tab(self) -> None:
        """Ask the notebook to create and select a fresh browser tab."""
        if self._on_new_tab is not None:
            self._on_new_tab()

    def apply_theme(self, theme_id: str | None = None) -> None:
        if theme_id is not None:
            self.service.set_theme(theme_id)
        self._toolbar.set_sensitive(True)

    def destroy(self) -> None:
        self.service.destroy()
        if WebKit is not None and self._browser is not None:
            self._browser.stop_loading()
            # GTK4 widgets do not expose the GTK3 ``destroy()`` method.
            # Removing this page from the notebook releases the WebView;
            # stopping it first prevents callbacks during teardown.
            self._browser = None


class _HeadlessToolbar:
    def set_sensitive(self, _sensitive: bool) -> None:
        pass


class _HeadlessButton:
    def __init__(self) -> None:
        self._sensitive = True
        self._label = ""

    def set_sensitive(self, sensitive: bool) -> None:
        self._sensitive = sensitive

    def set_tooltip_text(self, _text: str) -> None:
        pass

    def set_label(self, text: str) -> None:
        self._label = text

    def get_label(self) -> str:
        return self._label


class _HeadlessEntry:
    def __init__(self, value: str = "") -> None:
        self._value = value
        self._has_focus = False

    def get_text(self) -> str:
        return self._value

    def set_text(self, value: str) -> None:
        self._value = value

    def grab_focus(self) -> None:
        self._has_focus = True

    def has_focus(self) -> bool:
        return self._has_focus

    def select_region(self, _start: int, _end: int) -> None:
        pass


class _HeadlessLabel:
    def __init__(self, text: str = "") -> None:
        self._text = text

    def set_text(self, text: str) -> None:
        self._text = text

    def get_text(self) -> str:
        return self._text


class _HeadlessLayout:
    pass


class _HeadlessStack:
    def __init__(self) -> None:
        self.visible_child = "start"

    def add_named(self, _widget: object, _name: str) -> None:
        pass

    def set_visible_child_name(self, name: str) -> None:
        self.visible_child = name

    def get_visible_child_name(self) -> str:
        return self.visible_child
