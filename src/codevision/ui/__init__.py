"""GTK user interface package for CodeVision.

This package holds the desktop workspace layout and widgets used to present the
project explorer, editor, and analysis panels in the main IDE window.
"""

from .main_window import CodeVisionWindow

__all__ = ["CodeVisionWindow"]
