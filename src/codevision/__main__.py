"""Module entry point for running the package as `python -m codevision`.

This keeps the launch path consistent with standard Python package patterns and
allows the app to be started without a custom shell script.
"""

from .main import main

if __name__ == "__main__":
    raise SystemExit(main())
