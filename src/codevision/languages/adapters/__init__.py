"""Language adapter stubs for the Phase 1 registry foundation.

The project already has a working C/C++ AST parser. This package keeps the
multi-language abstraction explicit without forcing unsupported adapters to
pretend they can parse every source format.
"""

from ..base import LanguageAdapter

__all__ = ["LanguageAdapter"]
