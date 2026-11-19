from __future__ import annotations


class ExportError(RuntimeError):
    """Base export-system error."""


class SerializationError(ExportError):
    """Raised when an analysis value cannot be serialized safely."""


class ExportValidationError(ExportError):
    """Raised when output or report validation fails."""
