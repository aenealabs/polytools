"""
Python type annotation → JSON Schema conversion.

Pure Python stdlib only (typing, inspect). No third-party dependencies.

Supported annotations
---------------------
Primitives      : str, int, float, bool, bytes, None / type(None)
Generics        : list[T], dict[K, V], tuple[T, ...], set[T], frozenset[T]
Typing aliases  : List[T], Dict[K, V], Tuple[...], Set[T], FrozenSet[T]
Optionals       : Optional[T]  →  anyOf: [T_schema, {type: null}]
Unions          : Union[T1, T2, ...]  →  anyOf: [...]
Literals        : Literal["a", "b"]  →  {type: string, enum: [...]}
Any             : Any  →  {} (no constraints)
Unknown         : falls back to {type: object}
"""

from __future__ import annotations

import inspect
import sys
import typing
from typing import Any, Union

# ---------------------------------------------------------------------------
# Compatibility helpers
# ---------------------------------------------------------------------------

def _get_origin(tp: Any) -> Any:
    return typing.get_origin(tp)


def _get_args(tp: Any) -> tuple:
    return typing.get_args(tp)


# Grab Literal safely across Python 3.8+
try:
    from typing import Literal as _Literal
    _LITERAL_ORIGIN = _get_origin(_Literal["_sentinel"])  # typing.Literal
except ImportError:
    _Literal = None  # type: ignore[assignment]
    _LITERAL_ORIGIN = None


# ---------------------------------------------------------------------------
# Primitive type map
# ---------------------------------------------------------------------------

_PRIMITIVES: dict[Any, dict] = {
    str:        {"type": "string"},
    int:        {"type": "integer"},
    float:      {"type": "number"},
    bool:       {"type": "boolean"},
    bytes:      {"type": "string", "format": "byte"},
    type(None): {"type": "null"},
    # Bare (non-generic) collection types
    list:       {"type": "array"},
    tuple:      {"type": "array"},
    set:        {"type": "array", "uniqueItems": True},
    frozenset:  {"type": "array", "uniqueItems": True},
    dict:       {"type": "object"},
}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def annotation_to_schema(annotation: Any) -> dict:
    """Convert a single Python type annotation to a JSON Schema dict.

    Returns an empty dict ``{}`` for missing annotations or ``typing.Any``,
    which in JSON Schema means "no constraints" (any value is valid).

    This function is deliberately non-recursive on exceptions: if a nested
    annotation cannot be resolved, that subtree falls back to ``{}``.
    """
    if annotation is inspect.Parameter.empty:
        return {}

    # typing.Any → unconstrained
    if annotation is Any:
        return {}

    # Primitive types
    if annotation in _PRIMITIVES:
        return dict(_PRIMITIVES[annotation])  # return a copy, never mutate

    origin = _get_origin(annotation)
    args = _get_args(annotation)

    # ------------------------------------------------------------------
    # Union / Optional
    # ------------------------------------------------------------------
    if origin is Union:
        non_none = [a for a in args if a is not type(None)]
        has_none = type(None) in args

        if len(non_none) == 1 and has_none:
            # Optional[X]  →  anyOf: [X_schema, null]
            inner = annotation_to_schema(non_none[0])
            return {"anyOf": [inner, {"type": "null"}]}

        # Union[X, Y, …]
        return {"anyOf": [annotation_to_schema(a) for a in args]}

    # ------------------------------------------------------------------
    # Literal
    # ------------------------------------------------------------------
    if _LITERAL_ORIGIN is not None and origin is _LITERAL_ORIGIN:
        values = list(args)
        if all(isinstance(v, str) for v in values):
            return {"type": "string", "enum": values}
        if all(isinstance(v, bool) for v in values):
            return {"type": "boolean", "enum": values}
        if all(isinstance(v, int) for v in values):
            return {"type": "integer", "enum": values}
        if all(isinstance(v, float) for v in values):
            return {"type": "number", "enum": values}
        # Mixed literal → bare enum (no type constraint)
        return {"enum": values}

    # ------------------------------------------------------------------
    # list / List[T]
    # ------------------------------------------------------------------
    if origin is list:
        schema: dict = {"type": "array"}
        if args:
            schema["items"] = annotation_to_schema(args[0])
        return schema

    # ------------------------------------------------------------------
    # dict / Dict[K, V]
    # ------------------------------------------------------------------
    if origin is dict:
        schema = {"type": "object"}
        if len(args) == 2:
            schema["additionalProperties"] = annotation_to_schema(args[1])
        return schema

    # ------------------------------------------------------------------
    # tuple / Tuple[T, ...] or Tuple[T1, T2, T3]
    # ------------------------------------------------------------------
    if origin is tuple:
        schema = {"type": "array"}
        if args:
            if len(args) == 2 and args[1] is Ellipsis:
                # Tuple[T, ...] — homogeneous, variable length
                schema["items"] = annotation_to_schema(args[0])
            else:
                # Tuple[T1, T2, T3] — heterogeneous, fixed length
                schema["prefixItems"] = [annotation_to_schema(a) for a in args]
                schema["minItems"] = len(args)
                schema["maxItems"] = len(args)
        return schema

    # ------------------------------------------------------------------
    # set / Set[T], frozenset / FrozenSet[T]
    # ------------------------------------------------------------------
    if origin in (set, frozenset):
        schema = {"type": "array", "uniqueItems": True}
        if args:
            schema["items"] = annotation_to_schema(args[0])
        return schema

    # ------------------------------------------------------------------
    # Fallback: treat unknown types as object
    # ------------------------------------------------------------------
    return {"type": "object"}
