"""Fast, bounded workspace filesystem search."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


DEFAULT_IGNORED_DIRECTORIES = frozenset(
    {
        ".git",
        "__pycache__",
        ".pytest_cache",
        ".venv",
        "venv",
        "build",
        "dist",
        "node_modules",
    }
)


@dataclass(frozen=True, slots=True)
class FileSearchConfig:
    """Options controlling workspace search without coupling them to the UI."""

    ignored_directories: frozenset[str] = field(
        default_factory=lambda: DEFAULT_IGNORED_DIRECTORIES
    )
    result_limit: int = 100


@dataclass(frozen=True, slots=True)
class SearchResult:
    name: str
    path: Path
    relative_path: Path
    is_file: bool
    is_directory: bool
    is_hidden: bool
    match_type: str
    score: tuple[int, int, int, int, str, str]
    match_indices: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class SearchResults:
    entries: tuple[SearchResult, ...]
    total_count: int


class FileSearchService:
    """Search a project tree without following directory symlinks."""

    def __init__(self, config: FileSearchConfig | None = None) -> None:
        self.config = config or FileSearchConfig()
        self._executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="codevision-search"
        )

    def search(self, workspace_root: Path, keyword: str) -> SearchResults:
        """Return deterministic, ranked matches for ``keyword``.

        Empty queries intentionally do no filesystem traversal.
        """
        query = keyword.casefold().strip()
        root = workspace_root.expanduser().resolve()
        if not query or not root.is_dir():
            return SearchResults((), 0)

        matches: list[SearchResult] = []
        for path, is_directory in self._walk(root):
            name = path.name
            match = _match_name(name, query)
            if match is None:
                continue
            match_type, position, indices = match
            hidden = name.startswith(".")
            # Category deliberately precedes relevance: ordinary files, ordinary
            # folders, hidden files, then hidden folders.
            category = 3 if hidden and is_directory else 2 if hidden else int(is_directory)
            score = (
                category,
                match_type,
                position,
                len(name),
                name.casefold(),
                path.relative_to(root).as_posix(),
            )
            matches.append(
                SearchResult(
                    name=name,
                    path=path,
                    relative_path=path.relative_to(root),
                    is_file=not is_directory,
                    is_directory=is_directory,
                    is_hidden=hidden,
                    match_type=("exact", "prefix", "contains", "fuzzy")[match_type],
                    score=score,
                    match_indices=indices,
                )
            )

        matches.sort(key=lambda result: result.score)
        return SearchResults(tuple(matches[: self.config.result_limit]), len(matches))

    def submit(self, workspace_root: Path, keyword: str):
        """Submit a search for callers that own their own request generation."""
        return self._executor.submit(self.search, workspace_root, keyword)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)

    def _walk(self, root: Path) -> Iterable[tuple[Path, bool]]:
        pending = [root]
        while pending:
            directory = pending.pop()
            try:
                with os.scandir(directory) as entries:
                    children = sorted(entries, key=lambda entry: entry.name.casefold())
                    for entry in children:
                        path = Path(entry.path)
                        try:
                            is_directory = entry.is_dir(follow_symlinks=False)
                            if is_directory:
                                if entry.name not in self.config.ignored_directories:
                                    yield path, True
                                    pending.append(path)
                                continue
                            # A symlink to a file is useful as a result, while a
                            # symlink to a directory is never traversed.
                            if entry.is_file(follow_symlinks=True):
                                yield path, False
                        except OSError:
                            continue
            except OSError:
                continue


def _match_name(name: str, query: str) -> tuple[int, int, tuple[int, ...]] | None:
    folded = name.casefold()
    if folded == query:
        return 0, 0, tuple(range(len(name)))
    if folded.startswith(query):
        return 1, 0, tuple(range(len(query)))
    position = folded.find(query)
    if position >= 0:
        return 2, position, tuple(range(position, position + len(query)))

    indices: list[int] = []
    cursor = 0
    for character in query:
        cursor = folded.find(character, cursor)
        if cursor < 0:
            return None
        indices.append(cursor)
        cursor += 1
    # Cap the looseness of fuzzy matches: a match must be reasonably compact.
    span = indices[-1] - indices[0] + 1
    if span > max(len(query) * 4, 8):
        return None
    return 3, indices[0], tuple(indices)
