REM ==========================================
REM 1.This file is for those SUCKERS who use Windows and want to run/work on CodeVision.
REM ==========================================

python --version
@echo off
setlocal EnableExtensions EnableDelayedExpansion

title CodeVision Dependency Setup - Windows

echo ==========================================
echo        CodeVision Dependency Setup
echo              Windows Edition
echo ==========================================
echo.

REM ==================================================
REM 1. Check Windows
REM ==================================================

echo [1/9] Checking operating system...

ver >nul 2>&1
if errorlevel 1 (
    echo ERROR: Unable to verify Windows.
    exit /b 1
)

echo Windows detected.
echo.

REM ==================================================
REM 2. Check Python
REM ==================================================

echo [2/9] Checking Python...

where python >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: Python 3 was not found.
    echo.
    echo Install Python 3.11 or newer and make sure
    echo "Add Python to PATH" is enabled during installation.
    echo.
    pause
    exit /b 1
)

python --version

python -c "import sys; print('Python executable:', sys.executable)"
if errorlevel 1 (
    echo ERROR: Python is not working correctly.
    pause
    exit /b 1
)

echo.

REM ==================================================
REM 3. Check Git
REM ==================================================

echo [3/9] Checking Git...

where git >nul 2>&1
if errorlevel 1 (
    echo WARNING: Git was not found.
    echo.
    echo CodeVision itself may still work, but Git is required
    echo for normal project development.
    echo.
    echo Install Git from:
    echo https://git-scm.com/download/win
    echo.
) else (
    git --version
)

echo.

REM ==================================================
REM 4. Check MSYS2
REM ==================================================

echo [4/9] Checking MSYS2...

set "MSYS2_ROOT=C:\msys64"

if not exist "%MSYS2_ROOT%\usr\bin\bash.exe" (
    echo.
    echo MSYS2 was not found at:
    echo     %MSYS2_ROOT%
    echo.
    echo CodeVision requires MSYS2 for the Windows GTK stack.
    echo.
    echo Install MSYS2 from:
    echo https://www.msys2.org/
    echo.
    echo After installation, run:
    echo     C:\msys64\usr\bin\bash.exe -lc "pacman -Syu"
    echo.
    echo Then run this script again.
    echo.
    pause
    exit /b 1
)

echo MSYS2 found: %MSYS2_ROOT%
echo.

REM ==================================================
REM 5. Update MSYS2 package database
REM ==================================================

echo [5/9] Updating MSYS2 packages...
echo.

"%MSYS2_ROOT%\usr\bin\bash.exe" -lc "pacman -Sy --noconfirm"

if errorlevel 1 (
    echo.
    echo ERROR: MSYS2 package database update failed.
    echo.
    echo Open MSYS2 UCRT64 and run:
    echo     pacman -Syu
    echo.
    pause
    exit /b 1
)

echo.

REM ==================================================
REM 6. Install GTK / GtkSourceView / Cairo / Graphviz
REM ==================================================

echo [6/9] Installing CodeVision native dependencies...
echo.

"%MSYS2_ROOT%\usr\bin\bash.exe" -lc "pacman -S --needed --noconfirm mingw-w64-ucrt-x86_64-python mingw-w64-ucrt-x86_64-python-pip mingw-w64-ucrt-x86_64-python-gobject mingw-w64-ucrt-x86_64-python-cairo mingw-w64-ucrt-x86_64-gtk4 mingw-w64-ucrt-x86_64-gtksourceview5 mingw-w64-ucrt-x86_64-gobject-introspection mingw-w64-ucrt-x86_64-cairo mingw-w64-ucrt-x86_64-graphviz mingw-w64-ucrt-x86_64-toolchain"

if errorlevel 1 (
    echo.
    echo ERROR: Failed to install MSYS2 dependencies.
    echo.
    pause
    exit /b 1
)

echo.

REM ==================================================
REM 7. Create Python virtual environment
REM ==================================================

echo [7/9] Creating Python virtual environment...
echo.

if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv

    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )

    echo Virtual environment created:
    echo     .venv
) else (
    echo Virtual environment already exists.
)

echo.

REM ==================================================
REM 8. Install Python dependencies
REM ==================================================

echo [8/9] Installing CodeVision Python dependencies...
echo.

call ".venv\Scripts\python.exe" -m pip install --upgrade pip setuptools wheel

if errorlevel 1 (
    echo ERROR: Failed to update Python packaging tools.
    pause
    exit /b 1
)

call ".venv\Scripts\python.exe" -m pip install ^
    tree-sitter ^
    tree-sitter-c ^
    tree-sitter-cpp ^
    networkx ^
    reportlab ^
    pytest ^
    pyinstaller

if errorlevel 1 (
    echo.
    echo ERROR: Failed to install Python dependencies.
    pause
    exit /b 1
)

echo.

REM ==================================================
REM 9. Verification
REM ==================================================

echo ==========================================
echo        Verifying CodeVision Setup
echo ==========================================
echo.

echo ---- Python ----
call ".venv\Scripts\python.exe" --version

echo.
echo ---- Tree-sitter ----
call ".venv\Scripts\python.exe" -c "import tree_sitter; print('Tree-sitter: OK')"

echo.
echo ---- Tree-sitter C ----
call ".venv\Scripts\python.exe" -c "import tree_sitter_c; print('Tree-sitter C: OK')"

echo.
echo ---- Tree-sitter C++ ----
call ".venv\Scripts\python.exe" -c "import tree_sitter_cpp; print('Tree-sitter C++: OK')"

echo.
echo ---- NetworkX ----
call ".venv\Scripts\python.exe" -c "import networkx; print('NetworkX:', networkx.__version__)"

echo.
echo ---- ReportLab ----
call ".venv\Scripts\python.exe" -c "import reportlab; print('ReportLab: OK')"

echo.
echo ---- PyInstaller ----
call ".venv\Scripts\pyinstaller.exe" --version

echo.
echo ---- GTK 4 ----
"%MSYS2_ROOT%\ucrt64\bin\bash.exe" -lc "python -c \"import gi; gi.require_version('Gtk', '4.0'); from gi.repository import Gtk; print('GTK 4: OK')\""

echo.
echo ---- GtkSourceView 5 ----
"%MSYS2_ROOT%\ucrt64\bin\bash.exe" -lc "python -c \"import gi; gi.require_version('GtkSource', '5'); from gi.repository import GtkSource; print('GtkSourceView 5: OK')\""

echo.
echo ---- PyCairo ----
"%MSYS2_ROOT%\ucrt64\bin\bash.exe" -lc "python -c \"import cairo; print('PyCairo: OK')\""

echo.
echo ---- Graphviz ----
"%MSYS2_ROOT%\ucrt64\bin\dot.exe" -V

echo.
echo ==========================================
echo       CodeVision setup complete!
echo ==========================================
echo.
echo Virtual environment:
echo     .venv\
echo.
echo Activate it with:
echo     .venv\Scripts\activate
echo.
echo Run Python with:
echo     .venv\Scripts\python.exe
echo.
echo Or activate first:
echo     .venv\Scripts\activate
echo     python
echo.
pause

endlocal
```
