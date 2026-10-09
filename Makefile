# Local development workflow and project bootstrap commands.
# Keep all generated artifacts under ./build so the source tree stays clean.
VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
BUILD_DIR := build
SITE_PACKAGES := $(BUILD_DIR)/site-packages
DIST_DIR := $(BUILD_DIR)/dist
SPEC_DIR := $(BUILD_DIR)/spec
WORK_DIR := $(BUILD_DIR)/pyinstaller
PYCACHE_DIR := $(BUILD_DIR)/pycache
PIP_CACHE_DIR := $(BUILD_DIR)/pip-cache
BINARY_NAME := codevision

.PHONY: install run test clean build-binary

install:
	# Create the build directories before any package or binary output is generated.
	mkdir -p $(BUILD_DIR) $(SITE_PACKAGES) $(DIST_DIR) $(SPEC_DIR) $(WORK_DIR) $(PYCACHE_DIR) $(PIP_CACHE_DIR)
	# Use system GTK bindings when available; this avoids the PyGObject source build issue on Debian/Ubuntu.
	python3 -m venv --system-site-packages $(VENV)
	PIP_CACHE_DIR="$(PIP_CACHE_DIR)" PYTHONPYCACHEPREFIX="$(PYCACHE_DIR)" $(PIP) install --upgrade pip
	PIP_CACHE_DIR="$(PIP_CACHE_DIR)" PYTHONPYCACHEPREFIX="$(PYCACHE_DIR)" $(PIP) install -r requirements.txt
	rm -rf $(SITE_PACKAGES)
	# Setuptools writes egg-info to build/ (see setup.cfg); install the package under build/ too.
	PIP_CACHE_DIR="$(PIP_CACHE_DIR)" PYTHONPYCACHEPREFIX="$(PYCACHE_DIR)" $(PIP) install --no-deps --target $(SITE_PACKAGES) .

run:
	# Run from the source tree while also resolving the build-local package copy.
	PYTHONPYCACHEPREFIX="$(PYCACHE_DIR)" PYTHONPATH="src:$(SITE_PACKAGES)" $(PYTHON) -m codevision

test:
	# Keep test runs aligned with the same source import path.
	PYTHONPYCACHEPREFIX="$(PYCACHE_DIR)" PYTHONPATH="src:$(SITE_PACKAGES)" $(PYTHON) -m pytest -q

build-binary:
	# Build any executable output under the project build tree only.
	mkdir -p $(BUILD_DIR) $(DIST_DIR) $(SPEC_DIR) $(WORK_DIR) $(PYCACHE_DIR)
	PYTHONPYCACHEPREFIX="$(PYCACHE_DIR)" $(PYTHON) -m PyInstaller --distpath "$(DIST_DIR)" --workpath "$(WORK_DIR)" --specpath "$(SPEC_DIR)" --onefile --name "$(BINARY_NAME)" src/codevision/__main__.py

clean:
	# Remove cached Python artifacts and generated build output, but never leave dist or binary output in the repo root.
	rm -rf .pytest_cache $(BUILD_DIR) dist *.egg-info src/*.egg-info
	find src tests -type d -name __pycache__ -prune -exec rm -rf {} +
	mkdir -p $(BUILD_DIR)
