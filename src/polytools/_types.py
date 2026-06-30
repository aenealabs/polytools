"""
Internal data types for polytools.

These are the intermediate representation (IR) between a Python function
and any provider-specific schema format. All provider formatters consume
FunctionMeta and produce a provider-specific dict.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any


# Sentinel — distinct from None so we can detect "no annotation" vs "-> None"
_EMPTY = inspect.Parameter.empty


@dataclass(frozen=True)
class ParamMeta:
    """Metadata extracted from a single function parameter."""

    name: str
    """The parameter name as it appears in the function signature."""

    annotation: Any
    """The raw Python type annotation (or inspect.Parameter.empty if absent)."""

    json_schema: dict
    """JSON Schema dict derived from the annotation. May be {} if annotation
    is absent or Any."""

    description: str = ""
    """Description parsed from the function's docstring, if available."""

    required: bool = True
    """True if the parameter has no default value."""

    default: Any = field(default=_EMPTY, compare=False)
    """The default value, or inspect.Parameter.empty if none."""


@dataclass(frozen=True)
class FunctionMeta:
    """All metadata extracted from a decorated function."""

    name: str
    """The function's __name__."""

    description: str
    """The summary line extracted from the docstring."""

    params: tuple[ParamMeta, ...]
    """Ordered tuple of parameter metadata (excludes self/cls)."""

    return_annotation: Any = _EMPTY
    """The raw return type annotation, or inspect.Parameter.empty if absent."""
