# Local development workflow and project bootstrap commands.
# Keep all generated build artifacts under ./build so the source tree remains clean.
VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
BUILD_DIR := build
SITE_PACKAGES := $(BUILD_DIR)/site-packages

.PHONY: install run test clean

install:
	# Create the project build directory first to keep generated output predictable.
	mkdir -p $(BUILD_DIR)
	# Use system GTK bindings when available; this avoids the PyGObject source build issue on Debian/Ubuntu.
	python3 -m venv --system-site-packages $(VENV)
	PYTHONPYCACHEPREFIX="$(BUILD_DIR)/pycache" $(PIP) install --upgrade pip
	PYTHONPYCACHEPREFIX="$(BUILD_DIR)/pycache" $(PIP) install -r requirements.txt
	rm -rf $(SITE_PACKAGES)
	# Install the package into the dedicated build area instead of leaving metadata in src/.
	PYTHONPYCACHEPREFIX="$(BUILD_DIR)/pycache" $(PIP) install --no-deps --target $(SITE_PACKAGES) .

run:
	# Run from the source tree while also resolving the build-local package copy.
	PYTHONPYCACHEPREFIX="$(BUILD_DIR)/pycache" PYTHONPATH="src:$(SITE_PACKAGES)" $(PYTHON) -m codevision

test:
	# Keep test runs aligned with the same source import path.
	PYTHONPYCACHEPREFIX="$(BUILD_DIR)/pycache" PYTHONPATH="src:$(SITE_PACKAGES)" $(PYTHON) -m pytest -q

clean:
	# Remove cached Python artifacts and generated build output.
	rm -rf .pytest_cache $(BUILD_DIR) dist *.egg-info src/*.egg-info
	find src tests -type d -name __pycache__ -prune -exec rm -rf {} +
	mkdir -p $(BUILD_DIR)
