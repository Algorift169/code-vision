from __future__ import annotations

import re
from urllib.parse import quote_plus


class KongBrowserService:
    """Browser state and URL normalization without GTK or WebKit dependencies."""

    DEFAULT_SEARCH_ENGINE = "https://duckduckgo.com/?q={query}"

    def __init__(
        self,
        initial_url: str | None = None,
        *,
        search_engine: str | None = None,
    ) -> None:
        self.search_engine = search_engine or self.DEFAULT_SEARCH_ENGINE
        self.history: list[str] = []
        self.history_index = -1
        self.current_url = ""
        self.page_title = "Kong Browser"
        self.loading = False
        self.theme_id = "obsidian-forge"
        self.destroyed = False
        if initial_url:
            self.load_url(initial_url)

    @staticmethod
    def _is_scheme_url(value: str) -> bool:
        return bool(re.match(r"^https?://", value, flags=re.IGNORECASE))

    @staticmethod
    def is_selected_url(value: str | None) -> bool:
        if value is None:
            return False
        candidate = value.strip()
        if not candidate:
            return False
        if KongBrowserService._is_scheme_url(candidate):
            return True
        return bool(
            re.match(
                r"^(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}(?:[/:?#].*)?$",
                candidate,
                flags=re.IGNORECASE,
            )
        )

    @staticmethod
    def is_valid_url(value: str | None) -> bool:
        return KongBrowserService.is_selected_url(value)

    def normalize_url(self, value: str | None) -> str:
        if value is None:
            return ""
        candidate = value.strip()
        if not candidate:
            return ""
        if self._is_scheme_url(candidate):
            return candidate
        if self.is_selected_url(candidate) and not any(ch.isspace() for ch in candidate):
            if candidate.startswith("www."):
                return "https://" + candidate
            if re.match(r"^(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}$", candidate, flags=re.IGNORECASE):
                return "https://" + candidate
            if candidate.startswith("localhost"):
                return "http://" + candidate
            if candidate.startswith("127.0.0.1"):
                return "http://" + candidate
            if candidate.startswith("file://"):
                return candidate
        encoded_query = quote_plus(candidate)
        return self.search_engine.format(query=encoded_query)

    def load_url(self, value: str | None) -> str:
        target = self.normalize_url(value)
        if not target:
            target = "https://example.com"
        if self.current_url and target == self.current_url:
            self.loading = True
            return self.current_url
        if self.history and self.history_index >= 0:
            self.history = self.history[: self.history_index + 1]
        self.history.append(target)
        self.history_index = len(self.history) - 1
        self.current_url = target
        self.loading = True
        if self.page_title == "Kong Browser":
            self.page_title = "Kong Browser"
        return self.current_url

    def go_back(self) -> str:
        if self.history_index <= 0:
            return self.current_url
        self.history_index -= 1
        self.current_url = self.history[self.history_index]
        self.loading = True
        return self.current_url

    def go_forward(self) -> str:
        if self.history_index >= len(self.history) - 1:
            return self.current_url
        self.history_index += 1
        self.current_url = self.history[self.history_index]
        self.loading = True
        return self.current_url

    def reload(self) -> str:
        if not self.current_url:
            self.current_url = "https://example.com"
        self.loading = True
        return self.current_url

    def stop(self) -> None:
        self.loading = False

    def set_loaded(self) -> None:
        self.loading = False

    def set_title(self, title: str | None) -> None:
        self.page_title = title.strip() if title and title.strip() else "Kong Browser"

    def set_theme(self, theme_id: str) -> None:
        self.theme_id = theme_id

    def destroy(self) -> None:
        self.destroyed = True
        self.stop()

    @classmethod
    def default_start_page(cls) -> str:
        return "https://example.com"
