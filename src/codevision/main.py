"""Thin command-line entry point for CodeVision."""

from __future__ import annotations

import sys


def main() -> int:
    """Delegate startup to the application lifecycle package."""
    try:
        from .app.application import main as run_application
    except (ImportError, ValueError, RuntimeError) as error:
        print(f"Failed to initialize CodeVision GTK UI: {error}", file=sys.stderr)
        return 1

    return run_application()


if __name__ == "__main__":
    raise SystemExit(main())
