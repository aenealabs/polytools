"""
OpenAI function-calling / tool-use schema format.

Spec: https://platform.openai.com/docs/guides/function-calling

Output shape:
{
    "type": "function",
    "function": {
        "name": "<name>",
        "description": "<description>",
        "parameters": {
            "type": "object",
            "properties": {
                "<param>": { ...json_schema... }
            },
            "required": ["<required_param>", ...]
        }
    }
}
"""

from __future__ import annotations

from .._types import FunctionMeta


def _build_param_schema(param) -> dict:
    """Merge JSON schema with description for a single parameter."""
    schema = dict(param.json_schema)  # shallow copy — never mutate originals
    if param.description:
        schema["description"] = param.description
    return schema


def to_openai(meta: FunctionMeta) -> dict:
    """Format a FunctionMeta as an OpenAI tool definition.

    Parameters
    ----------
    meta : FunctionMeta
        Intermediate representation from the inspector.

    Returns
    -------
    dict
        Ready to pass as an element of the ``tools`` list in the OpenAI
        Chat Completions API.
    """
    properties: dict[str, dict] = {}
    required: list[str] = []

    for param in meta.params:
        properties[param.name] = _build_param_schema(param)
        if param.required:
            required.append(param.name)

    parameters: dict = {
        "type": "object",
        "properties": properties,
    }
    if required:
        parameters["required"] = required

    tool: dict = {
        "type": "function",
        "function": {
            "name": meta.name,
            "description": meta.description,
            "parameters": parameters,
        },
    }
    return tool
