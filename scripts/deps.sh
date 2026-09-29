#So before u read this, make sure you have a Debian/Ubuntu/Kali-based system. This script is
# designed to set up the necessary dependencies for CodeVision, a code visualization tool. 
# It checks for the required packages, installs them, and sets up a Python virtual environment 
# with the necessary Python packages. It also verifies the installation of each component.
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

set -e

echo "=========================================="
echo "        CodeVision Dependency Setup"
echo "=========================================="
echo

# --------------------------------------------------
# 1. Check operating system
# --------------------------------------------------

if ! command -v apt >/dev/null 2>&1; then
    echo "ERROR: This script requires a Debian/Ubuntu/Kali-based system."
    exit 1
fi

# --------------------------------------------------
# 2. Update package database
# --------------------------------------------------

echo "[1/7] Updating package database..."
sudo apt update

# --------------------------------------------------
# 3. System dependencies
# --------------------------------------------------

echo
echo "[2/7] Installing system dependencies..."

sudo apt install -y \
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

# --------------------------------------------------
# 5. Create virtual environment
# --------------------------------------------------

echo
echo "[4/7] Creating Python virtual environment..."

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "Virtual environment created: .venv"
else
    echo "Virtual environment already exists."
fi

source .venv/bin/activate

# --------------------------------------------------
# 6. Upgrade Python build tools
# --------------------------------------------------

echo
echo "[5/7] Updating Python packaging tools..."

python -m pip install --upgrade pip setuptools wheel

# --------------------------------------------------
# 7. Install Python dependencies
# --------------------------------------------------

echo
echo "[6/7] Installing CodeVision Python dependencies..."

python -m pip install \
    PyGObject \
    pycairo \
    tree-sitter \
    tree-sitter-c \
    tree-sitter-cpp \
    networkx \
    reportlab \
    pytest \
    pyinstaller

# --------------------------------------------------
# 8. Verification
# --------------------------------------------------

echo
echo "[7/7] Verifying installation..."
echo

echo "---- Python ----"
python --version

echo
echo "---- GTK / PyGObject ----"
python -c "import gi; gi.require_version('Gtk', '4.0'); from gi.repository import Gtk; print('GTK 4: OK')"

echo
echo "---- GtkSourceView ----"
python -c "import gi; gi.require_version('GtkSource', '5'); from gi.repository import GtkSource; print('GtkSourceView 5: OK')"

echo
echo "---- Cairo ----"
python -c "import cairo; print('PyCairo: OK')"

echo
echo "---- Tree-sitter ----"
python -c "import tree_sitter; print('Tree-sitter: OK')"

echo
echo "---- Tree-sitter C ----"
python -c "import tree_sitter_c; print('Tree-sitter C: OK')"

echo
echo "---- Tree-sitter C++ ----"
python -c "import tree_sitter_cpp; print('Tree-sitter C++: OK')"

echo
echo "---- NetworkX ----"
python -c "import networkx; print('NetworkX:', networkx.__version__)"

echo
echo "---- ReportLab ----"
python -c "import reportlab; print('ReportLab: OK')"

echo
echo "---- PyInstaller ----"
pyinstaller --version

echo
echo "---- Graphviz ----"
dot -V

echo
echo "=========================================="
echo "       CodeVision setup complete!"
echo "=========================================="
echo
echo "Virtual environment:"
echo "    .venv/"
echo
echo "Activate it with:"
echo "    source .venv/bin/activate"
echo
echo "Run Python with:"
echo "    python"
echo