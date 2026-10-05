# CodeVision

CodeVision is a desktop application for browsing a project tree, editing files, and working with C/C++ code analysis tooling in a single window. The current codebase is a GTK 4-based desktop app with a project explorer, editor tabs, analysis panel, terminal support, and a configurable visual theme system.

## Current project status

This repository is in an active development state. The codebase already includes:

- a GTK application bootstrap and main window
- project explorer and file browsing flows
- editor/tab UI and terminal panel integration
- file rename/delete operations and path handling helpers
- configurable theme registry with multiple CSS theme files
- a test suite covering themes, file operations, menu actions, and selection/copy behavior

The code analyzer itself is not implemented yet. The project currently provides the editor and desktop shell foundation, but the actual C/C++ analysis engine, diagnostics generation, and deep code intelligence are still planned work.

This is not a fully complete IDE yet; it is a structured desktop app foundation with working UI and service-level functionality.

## Repository layout

- `src/codevision/` - Python package source
  - `app/` - GTK application bootstrap and window lifecycle
  - `ui/` - UI widgets, theme manager, and menu integrations
  - `services/` - project/file/operation support services
  - `editor/` - editor tab and editor-related components
  - `analysis/`, `compiler/`, `execution/`, `graphs/`, `memory/`, `model/`, `parser/`, `project/`, `utils/` - planned or partial subsystems, including the future code analysis stack
- `resources/styles/` - GTK CSS theme files
- `tests/` - pytest coverage for core behaviors
- `build/` - generated build artifacts and package output
- `Makefile` - local development build and cleanup commands

## Requirements

- Python 3.10+
- GTK 4 runtime (`PyGObject` / GI bindings)
- System packages for GTK and related UI dependencies

The package dependencies are listed in `requirements.txt` and the Python package metadata in `pyproject.toml`.

## Installation

From the project root:

```bash
python3 -m venv --system-site-packages .venv
. .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

The project also includes a Makefile for local setup and run commands:

```bash
make install
make run
make test
make clean
```

## Running the app

```bash
make run
```

This runs the GTK app using the project source and a build-local package path setup.

## Testing

```bash
test -q
```

or with the project Makefile:

```bash
make test
```

The current tests cover:

- theme registration and persistence
- file rename/delete behavior
- menu action enablement and validation
- path copying and relative path handling
- terminal copy/paste and selection behavior

## Build behavior

The project intentionally keeps generated artifacts under `build/` and avoids leaving binaries or package outputs in the source tree. The Makefile is configured to put build outputs such as PyInstaller output and cached items into `build/` rather than placing them at the repository root.

## Notes

- The application is currently structured as a desktop editor/analysis tool rather than a finished production IDE.
- The actual code analyzer is still to be implemented; the current project shell is ready for that next layer of functionality.
- UI styling is handled through GTK CSS theme files under `resources/styles/`.
- The current package is versioned as `0.1.0` and is still evolving.
