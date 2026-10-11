"""Maintain browser navigation state independently from GTK and WebKit."""

from __future__ import annotations

import re
from urllib.parse import quote_plus


class KongBrowserService:
    """Track browser URL, history, loading state, title, and theme.

    This service has no GTK or WebKit dependency, allowing navigation state
    and URL normalization to be managed separately from the browser widget.
    """

    DEFAULT_SEARCH_ENGINE = "https://duckduckgo.com/?q={query}"

    def __init__(
        self,
        initial_url: str | None = None,
        *,
        search_engine: str | None = None,
    ) -> None:
        """Initialize browser state and optionally load an initial address.

        Args:
            initial_url: Optional URL or search text to load after setup.
            search_engine: Search URL template with a ``{query}`` placeholder.
                The default template uses DuckDuckGo.
        """
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
        """Return whether a string begins with an HTTP or HTTPS scheme."""
        return bool(re.match(r"^https?://", value, flags=re.IGNORECASE))

    @staticmethod
    def is_selected_url(value: str | None) -> bool:
        """Report whether an address-bar value looks like a web address.

        HTTP(S) URLs are accepted directly. Scheme-less hostnames are accepted
        when they match the service's hostname pattern; empty input and other
        values are not considered selected URLs.
        """
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
        """Expose the same address recognition rule used by the URL field."""
        return KongBrowserService.is_selected_url(value)

    def normalize_url(self, value: str | None) -> str:
        """Normalize an address or turn arbitrary text into a search URL.

        Existing HTTP(S) values are preserved. Recognized scheme-less hosts
        receive an appropriate HTTP or HTTPS prefix; other non-empty values
        are URL-encoded and inserted into the configured search template.
        Empty or missing input returns an empty string.

        Args:
            value: Address-bar input to normalize.

        Returns:
            A navigable URL, search URL, or empty string.
        """
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
        """Navigate to a normalized target and update back/forward history.

        Empty input falls back to the service's default example page. Loading
        a URL already current marks the page as loading without adding a
        duplicate history item. New navigation discards any forward history.

        Args:
            value: URL or search text to load.

        Returns:
            The URL now recorded as current.
        """
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
        """Move to the preceding history entry when one is available.

        The current URL is returned unchanged at the beginning of history.
        """
        if self.history_index <= 0:
            return self.current_url
        self.history_index -= 1
        self.current_url = self.history[self.history_index]
        self.loading = True
        return self.current_url

    def go_forward(self) -> str:
        """Move to the next history entry when one is available.

        The current URL is returned unchanged at the end of history.
        """
        if self.history_index >= len(self.history) - 1:
            return self.current_url
        self.history_index += 1
        self.current_url = self.history[self.history_index]
        self.loading = True
        return self.current_url

    def reload(self) -> str:
        """Mark the current address for reloading and return it.

        When no address has been loaded yet, the default example page becomes
        the current URL. This updates service state but does not perform a
        network request itself.
        """
        if not self.current_url:
            self.current_url = "https://example.com"
        self.loading = True
        return self.current_url

    def stop(self) -> None:
        """Mark the current navigation as no longer loading."""
        self.loading = False

    def set_loaded(self) -> None:
        """Record that the current page finished loading."""
        self.loading = False

    def set_title(self, title: str | None) -> None:
        """Store a non-empty page title or restore the default browser title."""
        self.page_title = title.strip() if title and title.strip() else "Kong Browser"

    def set_theme(self, theme_id: str) -> None:
        """Store the selected theme identifier for the browser UI."""
        self.theme_id = theme_id

    def destroy(self) -> None:
        """Mark the browser service destroyed and clear its loading state."""
        self.destroyed = True
        self.stop()

    @classmethod
    def default_start_page(cls) -> str:
        """Return the default page URL used when navigation has no target."""
        return "https://example.com"
