# Set up CodeVision's system and Python dependencies on Debian-family systems.
#_______________________________________________________________________________________________________;
#           (``~)
#          ( ~ ~ )
#          (  O  )
#   ________\   /________
#  /  ______ \ / ______  \
# /  /      \   /      \  \
#|  |                   | |
#|  |        ---        | |
#|  |                   | |
#\  \                 /  /
# \  \_______________/  /
#   \___________________/
#      ||     ||     ||
#      ||     ||     ||
#     (__)   (__)   (__)

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
VENV_DIR="${PROJECT_ROOT}/.venv"
cd "${PROJECT_ROOT}"

echo "=========================================="
echo "        CodeVision Dependency Setup"
echo "=========================================="
echo

# --------------------------------------------------
# 1. Check operating system
# --------------------------------------------------

if ! command -v apt-get >/dev/null 2>&1 || [ ! -r /etc/os-release ]; then
    echo "ERROR: This script requires a Debian/Ubuntu/Kali-based system."
    exit 1
fi

if [ "${EUID}" -eq 0 ]; then
    SUDO=()
elif command -v sudo >/dev/null 2>&1; then
    SUDO=(sudo)
else
    echo "ERROR: Run as root or install sudo to install system dependencies."
    exit 1
fi

# --------------------------------------------------
# 2. Update package database
# --------------------------------------------------

echo "[1/7] Updating package database..."
"${SUDO[@]}" apt-get update

# --------------------------------------------------
# 3. System dependencies
# --------------------------------------------------

echo
echo "[2/7] Installing system dependencies..."

"${SUDO[@]}" apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    python3-gi \
    python3-gi-cairo \
    gir1.2-gtk-4.0 \
    gir1.2-gtksource-5 \
    gir1.2-vte-3.91 \
    libgtk-4-dev \
    libgtksourceview-5-dev \
    libgirepository1.0-dev \
    gobject-introspection \
    libcairo2-dev \
    pkg-config \
    graphviz \
    git \
    build-essential

# --------------------------------------------------
# 4. Verify Python
# --------------------------------------------------

echo
echo "[3/7] Checking Python..."

python3 --version
python3 -m pip --version

if ! python3 -c 'import sys; raise SystemExit(sys.version_info < (3, 10))'; then
    echo "ERROR: CodeVision requires Python 3.10 or newer."
    exit 1
fi

# --------------------------------------------------
# 5. Create virtual environment
# --------------------------------------------------

echo
echo "[4/7] Creating Python virtual environment..."

python3 -m venv --system-site-packages --upgrade "${VENV_DIR}"
echo "Virtual environment ready: ${VENV_DIR}"

# --------------------------------------------------
# 6. Upgrade Python build tools
# --------------------------------------------------

echo
echo "[5/7] Updating Python packaging tools..."

"${VENV_DIR}/bin/python" -m pip install --upgrade pip setuptools wheel

# --------------------------------------------------
# 7. Install Python dependencies
# --------------------------------------------------

echo
echo "[6/7] Installing CodeVision and its declared development dependencies..."

"${VENV_DIR}/bin/python" -m pip install --editable '.[dev]'

# --------------------------------------------------
# 8. Verification
# --------------------------------------------------

echo
echo "[7/7] Verifying installation..."
echo

echo "---- Python ----"
"${VENV_DIR}/bin/python" --version

echo
echo "---- GTK / PyGObject ----"
"${VENV_DIR}/bin/python" -c "import gi; gi.require_version('Gtk', '4.0'); from gi.repository import Gtk; print('GTK 4 / PyGObject: OK')"

echo
echo "---- GtkSourceView ----"
"${VENV_DIR}/bin/python" -c "import gi; gi.require_version('GtkSource', '5'); from gi.repository import GtkSource; print('GtkSourceView 5: OK')"

echo
echo "---- VTE terminal ----"
"${VENV_DIR}/bin/python" -c "import gi; gi.require_version('Vte', '3.91'); from gi.repository import Vte; print('VTE 3.91: OK')"

echo
echo "---- Cairo ----"
"${VENV_DIR}/bin/python" -c "import cairo; print('PyCairo: OK')"

echo
echo "---- Tree-sitter ----"
"${VENV_DIR}/bin/python" -c "import tree_sitter; print('Tree-sitter: OK')"

echo
echo "---- Tree-sitter C ----"
"${VENV_DIR}/bin/python" -c "import tree_sitter_c; print('Tree-sitter C: OK')"

echo
echo "---- Tree-sitter C++ ----"
"${VENV_DIR}/bin/python" -c "import tree_sitter_cpp; print('Tree-sitter C++: OK')"

echo
echo "---- NetworkX ----"
"${VENV_DIR}/bin/python" -c "import networkx; print('NetworkX:', networkx.__version__)"

echo
echo "---- Python Graphviz ----"
"${VENV_DIR}/bin/python" -c "import graphviz; print('Python Graphviz: OK')"

echo
echo "---- ReportLab ----"
"${VENV_DIR}/bin/python" -c "import reportlab; print('ReportLab: OK')"

echo
echo "---- PyInstaller ----"
"${VENV_DIR}/bin/pyinstaller" --version

echo
echo "---- Graphviz ----"
dot -V

echo
echo "---- Test and lint tools ----"
"${VENV_DIR}/bin/python" -m pytest --version
"${VENV_DIR}/bin/black" --version
"${VENV_DIR}/bin/ruff" --version

echo
echo "---- CodeVision command ----"
if [ ! -x "${VENV_DIR}/bin/codevision" ]; then
    echo "ERROR: CodeVision launcher was not installed."
    exit 1
fi
echo "CodeVision entry point: installed"

echo
echo "=========================================="
echo "       CodeVision setup complete!"
echo "=========================================="
echo
echo "Virtual environment:"
echo "    ${VENV_DIR}"
echo
echo "Activate it with:"
echo "    source .venv/bin/activate"
echo
echo "Run Python with:"
echo "    python"
echo