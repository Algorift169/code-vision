from __future__ import annotations

import dataclasses
import enum
from pathlib import Path
from typing import Any


_SERIALIZATION_ERRORS: list[dict[str, str]] = []


def clear_serialization_errors() -> None:
    _SERIALIZATION_ERRORS.clear()


def serialization_errors() -> list[dict[str, str]]:
    return [dict(error) for error in _SERIALIZATION_ERRORS]


def serialize_value(value: Any, source: str = "analysis") -> Any:
    """Convert supported and dataclass-based analysis values to JSON-safe data."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, enum.Enum):
        return serialize_value(value.value, source)
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, dict):
        return {str(key): serialize_value(item, f"{source}.{key}") for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [serialize_value(item, f"{source}[{index}]") for index, item in enumerate(value)]
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        result: dict[str, Any] = {"__type__": type(value).__name__}
        for field in dataclasses.fields(value):
            result[field.name] = serialize_value(getattr(value, field.name), f"{source}.{field.name}")
        return result

    _SERIALIZATION_ERRORS.append({
        "source": source,
        "type": type(value).__module__ + "." + type(value).__qualname__,
        "message": "Unsupported analysis value; exported as structured fallback metadata",
    })
    if hasattr(value, "__dict__"):
        return {
            "__type__": type(value).__name__,
            **serialize_value(vars(value), source),
        }
    return {
        "__type__": type(value).__name__,
        "value": repr(value),
    }
