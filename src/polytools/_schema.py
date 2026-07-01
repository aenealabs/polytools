"""
Python type annotation → JSON Schema conversion.

Pure Python stdlib only (typing, inspect, dataclasses, enum). No third-party
dependencies.

Supported annotations
---------------------
Primitives      : str, int, float, bool, bytes, None / type(None)
Generics        : list[T], dict[K, V], tuple[T, ...], set[T], frozenset[T]
Typing aliases  : List[T], Dict[K, V], Tuple[...], Set[T], FrozenSet[T]
Optionals       : Optional[T]  →  anyOf: [T_schema, {type: null}]
Unions          : Union[T1, T2, ...]  →  anyOf: [...]
Literals        : Literal["a", "b"]  →  {type: string, enum: [...]}
Enums           : enum.Enum subclass  →  {type: <value type>, enum: [...]}
Structured      : dataclass / TypedDict / NamedTuple
                  →  {type: object, properties: {...}, required: [...]}
Any             : Any  →  {} (no constraints)
Unknown         : falls back to {type: object}

Nested structured types are resolved recursively (e.g. a dataclass field that
is itself a dataclass, or ``list[SomeDataclass]``). Self-referential types are
guarded against infinite recursion and collapse to ``{type: object}``.
"""

from __future__ import annotations

import dataclasses
import enum
import inspect
import typing
from typing import Any, Union, get_type_hints

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
# Structured-type detection (dataclass / TypedDict / NamedTuple / Enum)
# ---------------------------------------------------------------------------

def _is_typeddict(tp: Any) -> bool:
    is_td = getattr(typing, "is_typeddict", None)  # Python 3.10+
    if is_td is not None:
        try:
            if is_td(tp):
                return True
        except Exception:  # pragma: no cover - defensive
            pass
    # Fallback for 3.9: TypedDict classes subclass dict and carry __total__.
    return (
        isinstance(tp, type)
        and issubclass(tp, dict)
        and hasattr(tp, "__annotations__")
        and hasattr(tp, "__total__")
    )


def _is_namedtuple(tp: Any) -> bool:
    return isinstance(tp, type) and issubclass(tp, tuple) and hasattr(tp, "_fields")


def _resolve_hints(cls: Any) -> dict:
    """typing.get_type_hints with a graceful fallback to raw annotations."""
    try:
        return get_type_hints(cls)
    except Exception:
        return dict(getattr(cls, "__annotations__", {}))


def _enum_to_schema(cls: type) -> dict:
    """Map an ``enum.Enum`` subclass to an enum schema, typed by its values."""
    values = [member.value for member in cls]
    if all(isinstance(v, str) for v in values):
        return {"type": "string", "enum": values}
    if all(isinstance(v, bool) for v in values):
        return {"type": "boolean", "enum": values}
    if all(isinstance(v, int) for v in values):
        return {"type": "integer", "enum": values}
    if all(isinstance(v, float) for v in values):
        return {"type": "number", "enum": values}
    return {"enum": values}  # mixed value types → untyped enum


def _dataclass_fields(cls: type) -> list:
    hints = _resolve_hints(cls)
    fields = []
    for f in dataclasses.fields(cls):
        annotation = hints.get(f.name, f.type)
        has_default = (
            f.default is not dataclasses.MISSING
            or f.default_factory is not dataclasses.MISSING  # type: ignore[misc]
        )
        fields.append((f.name, annotation, not has_default))
    return fields


def _typeddict_fields(td: type) -> list:
    hints = _resolve_hints(td)
    required_keys = getattr(td, "__required_keys__", None)
    if required_keys is None:
        total = getattr(td, "__total__", True)
        required_keys = set(hints) if total else set()
    return [(key, hints.get(key, Any), key in required_keys) for key in hints]


def _namedtuple_fields(nt: type) -> list:
    hints = _resolve_hints(nt)
    defaults = getattr(nt, "_field_defaults", {})
    return [(name, hints.get(name, Any), name not in defaults) for name in nt._fields]


def _object_schema(cls: type, fields: list, seen: frozenset) -> dict:
    """Build an object schema from ``(name, annotation, required)`` triples."""
    child_seen = seen | {cls}
    properties: dict[str, dict] = {}
    required: list[str] = []
    for name, annotation, is_required in fields:
        properties[name] = _to_schema(annotation, child_seen)
        if is_required:
            required.append(name)
    schema: dict = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def annotation_to_schema(annotation: Any) -> dict:
    """Convert a single Python type annotation to a JSON Schema dict.

    Returns an empty dict ``{}`` for missing annotations or ``typing.Any``,
    which in JSON Schema means "no constraints" (any value is valid).

    This function is deliberately non-recursive on exceptions: if a nested
    annotation cannot be resolved, that subtree falls back to ``{}`` or
    ``{"type": "object"}``.
    """
    return _to_schema(annotation, frozenset())


def _to_schema(annotation: Any, seen: frozenset) -> dict:
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
            inner = _to_schema(non_none[0], seen)
            return {"anyOf": [inner, {"type": "null"}]}

        # Union[X, Y, …]
        return {"anyOf": [_to_schema(a, seen) for a in args]}

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
            schema["items"] = _to_schema(args[0], seen)
        return schema

    # ------------------------------------------------------------------
    # dict / Dict[K, V]
    # ------------------------------------------------------------------
    if origin is dict:
        schema = {"type": "object"}
        if len(args) == 2:
            schema["additionalProperties"] = _to_schema(args[1], seen)
        return schema

    # ------------------------------------------------------------------
    # tuple / Tuple[T, ...] or Tuple[T1, T2, T3]
    # ------------------------------------------------------------------
    if origin is tuple:
        schema = {"type": "array"}
        if args:
            if len(args) == 2 and args[1] is Ellipsis:
                # Tuple[T, ...] — homogeneous, variable length
                schema["items"] = _to_schema(args[0], seen)
            else:
                # Tuple[T1, T2, T3] — heterogeneous, fixed length
                schema["prefixItems"] = [_to_schema(a, seen) for a in args]
                schema["minItems"] = len(args)
                schema["maxItems"] = len(args)
        return schema

    # ------------------------------------------------------------------
    # set / Set[T], frozenset / FrozenSet[T]
    # ------------------------------------------------------------------
    if origin in (set, frozenset):
        schema = {"type": "array", "uniqueItems": True}
        if args:
            schema["items"] = _to_schema(args[0], seen)
        return schema

    # ------------------------------------------------------------------
    # Structured class types: Enum, TypedDict, NamedTuple, dataclass
    # ------------------------------------------------------------------
    if isinstance(annotation, type):
        if issubclass(annotation, enum.Enum):
            return _enum_to_schema(annotation)

        # Guard against self-referential structures.
        if annotation in seen:
            return {"type": "object"}

        if _is_typeddict(annotation):
            return _object_schema(annotation, _typeddict_fields(annotation), seen)
        if _is_namedtuple(annotation):
            return _object_schema(annotation, _namedtuple_fields(annotation), seen)
        if dataclasses.is_dataclass(annotation):
            return _object_schema(annotation, _dataclass_fields(annotation), seen)

    # ------------------------------------------------------------------
    # Fallback: treat unknown types as object
    # ------------------------------------------------------------------
    return {"type": "object"}
