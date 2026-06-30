"""
Model Context Protocol (MCP) tool schema format.

Spec: https://spec.modelcontextprotocol.io/specification/server/tools/

Output shape:
{
    "name": "<name>",
    "description": "<description>",
    "inputSchema": {
        "type": "object",
        "properties": {
            "<param>": { ...json_schema... }
        },
        "required": ["<required_param>", ...]
    }
}

Key differences from OpenAI/Anthropic:
- No outer type wrapper
- Schema key is "inputSchema" (camelCase, vs Anthropic's "input_schema")
- inputSchema must be a JSON Schema object (standard lowercase types)
- MCP uses the JSON Schema draft-07 subset for maximum compatibility
"""

from __future__ import annotations

from .._types import FunctionMeta


def _build_param_schema(param) -> dict:
    schema = dict(param.json_schema)
    if param.description:
        schema["description"] = param.description
    return schema


def to_mcp(meta: FunctionMeta) -> dict:
    """Format a FunctionMeta as an MCP tool definition.

    Parameters
    ----------
    meta : FunctionMeta
        Intermediate representation from the inspector.

    Returns
    -------
    dict
        Ready to pass as an element of the ``tools`` list in an MCP
        ``tools/list`` response (ListToolsResult).
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
        "inputSchema": input_schema,
    }
