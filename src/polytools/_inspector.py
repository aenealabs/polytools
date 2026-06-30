"""
Function inspector — bridges Python introspection with polytools' IR.

Uses only stdlib: inspect, typing.
"""

from __future__ import annotations

import inspect
from typing import Any, Callable, get_type_hints

from ._docstring import parse_docstring
from ._schema import annotation_to_schema
from ._types import FunctionMeta, ParamMeta, _EMPTY


def inspect_function(func: Callable) -> FunctionMeta:
    """Extract FunctionMeta from a Python callable.

    Parameters
    ----------
    func : Callable
        Any function or bound/unbound method.

    Returns
    -------
    FunctionMeta
        Structured metadata ready for provider formatters.

    Notes
    -----
    - ``self`` and ``cls`` parameters are automatically excluded.
    - ``*args`` and ``**kwargs`` are currently excluded (variadic params
      cannot be meaningfully represented in JSON Schema tool definitions).
    - If ``typing.get_type_hints()`` fails (e.g. forward references that
      cannot be resolved), we fall back to the raw ``__annotations__`` dict.
    - Docstring parsing is best-effort; missing descriptions become ``""``.
    """
    # ------------------------------------------------------------------
    # 1. Resolve type hints
    # ------------------------------------------------------------------
    try:
        hints = get_type_hints(func)
    except Exception:
        # Forward references that can't be resolved, C extensions, etc.
        hints = getattr(func, "__annotations__", {})

    # ------------------------------------------------------------------
    # 2. Get signature
    # ------------------------------------------------------------------
    try:
        sig = inspect.signature(func)
    except (ValueError, TypeError):
        # Some builtins don't expose a Python-level signature
        sig = None

    # ------------------------------------------------------------------
    # 3. Parse docstring
    # ------------------------------------------------------------------
    raw_doc = inspect.getdoc(func) or ""
    doc_info = parse_docstring(raw_doc)

    # ------------------------------------------------------------------
    # 4. Build ParamMeta for each parameter
    # ------------------------------------------------------------------
    params: list[ParamMeta] = []

    if sig is not None:
        for name, param in sig.parameters.items():
            # Skip self/cls (instance and class methods)
            if name in ("self", "cls"):
                continue

            # Skip *args and **kwargs — not representable as JSON Schema tools
            if param.kind in (
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            ):
                continue

            annotation = hints.get(name, _EMPTY)
            json_schema = annotation_to_schema(annotation)

            required = param.default is inspect.Parameter.empty
            default = _EMPTY if required else param.default

            params.append(
                ParamMeta(
                    name=name,
                    annotation=annotation,
                    json_schema=json_schema,
                    description=doc_info.params.get(name, ""),
                    required=required,
                    default=default,
                )
            )

    # ------------------------------------------------------------------
    # 5. Assemble FunctionMeta
    # ------------------------------------------------------------------
    return FunctionMeta(
        name=func.__name__,
        description=doc_info.summary,
        params=tuple(params),
        return_annotation=hints.get("return", _EMPTY),
    )
