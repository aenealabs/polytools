"""
Anthropic tool-use schema format.

Spec: https://docs.anthropic.com/en/docs/tool-use

Output shape:
{
    "name": "<name>",
    "description": "<description>",
    "input_schema": {
        "type": "object",
        "properties": {
            "<param>": { ...json_schema... }
        },
        "required": ["<required_param>", ...]
    }
}

Key differences from OpenAI:
- No outer "type": "function" wrapper
- Schema key is "input_schema" not "parameters"
"""

from __future__ import annotations

from .._types import FunctionMeta


def _build_param_schema(param) -> dict:
    schema = dict(param.json_schema)
    if param.description:
        schema["description"] = param.description
    return schema


def to_anthropic(meta: FunctionMeta) -> dict:
    """Format a FunctionMeta as an Anthropic tool definition.

    Parameters
    ----------
    meta : FunctionMeta
        Intermediate representation from the inspector.

    Returns
    -------
    dict
        Ready to pass as an element of the ``tools`` list in the Anthropic
        Messages API.
    """
    properties: dict[str, dict] = {}
    required: list[str] = []

    for param in meta.params:
        properties[param.name] = _build_param_schema(param)
        if param.required:
            required.append(param.name)

    input_schema: dict = {
        "type": "object",
        "properties": properties,
    }
    if required:
        input_schema["required"] = required

    return {
        "name": meta.name,
        "description": meta.description,
        "input_schema": input_schema,
    }
