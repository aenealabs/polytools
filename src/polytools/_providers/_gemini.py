"""
Google Gemini function-declaration schema format.

Spec: https://ai.google.dev/api/generate-content#v1beta.FunctionDeclaration

Output shape:
{
    "name": "<name>",
    "description": "<description>",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "<param>": { "type": "STRING", ... }
        },
        "required": ["<required_param>", ...]
    }
}

Key differences from OpenAI/Anthropic:
- JSON Schema type names are UPPERCASE ("STRING", "INTEGER", "NUMBER",
  "BOOLEAN", "ARRAY", "OBJECT", "NULL") — Gemini uses an enum, not the
  JSON Schema standard lowercase strings.
- No outer wrapper (like OpenAI's "type": "function")
- Schema key is "parameters" (same key as OpenAI but different type casing)
"""

from __future__ import annotations

from .._types import FunctionMeta

# ---------------------------------------------------------------------------
# Gemini uses uppercase type enums
# ---------------------------------------------------------------------------

_JSON_TO_GEMINI_TYPE: dict[str, str] = {
    "string":  "STRING",
    "integer": "INTEGER",
    "number":  "NUMBER",
    "boolean": "BOOLEAN",
    "array":   "ARRAY",
    "object":  "OBJECT",
    "null":    "NULL",
}


def _convert_schema(schema: dict) -> dict:
    """Recursively convert a JSON Schema dict to Gemini's format.

    Gemini does not support the full JSON Schema spec; this conversion
    handles the most common constructs that arise from Python type hints.

    ``anyOf`` (used for Optional and Union) is converted by picking the
    first non-null entry as the primary type, since Gemini's API does not
    support anyOf natively. Nullability is expressed by omitting the field
    from ``required`` instead.
    """
    if not schema:
        return schema

    result: dict = {}

    for key, value in schema.items():
        if key == "type" and isinstance(value, str):
            result["type"] = _JSON_TO_GEMINI_TYPE.get(value, value.upper())

        elif key == "items" and isinstance(value, dict):
            result["items"] = _convert_schema(value)

        elif key == "properties" and isinstance(value, dict):
            result["properties"] = {
                k: _convert_schema(v) for k, v in value.items()
            }

        elif key == "prefixItems" and isinstance(value, list):
            # Gemini doesn't support tuple schemas; flatten to array
            result["type"] = "ARRAY"
            # Best effort: use the first item type if uniform
            if value:
                result["items"] = _convert_schema(value[0])

        elif key == "anyOf" and isinstance(value, list):
            # anyOf (Optional/Union) — Gemini doesn't support anyOf.
            # Strategy: pick the first non-null schema as the canonical type.
            non_null = [_convert_schema(s) for s in value
                        if s != {"type": "null"} and s.get("type") != "null"]
            if non_null:
                result.update(non_null[0])
            # Nullability handled by not listing the param in required

        elif key == "enum":
            result["enum"] = value

        elif key == "additionalProperties" and isinstance(value, dict):
            result["additionalProperties"] = _convert_schema(value)

        elif key == "required" and isinstance(value, list):
            # Preserve required lists on nested object schemas.
            result["required"] = value

        elif key in ("description", "format", "minItems", "maxItems",
                     "uniqueItems", "minimum", "maximum"):
            result[key] = value

        # Keys not supported by Gemini are silently dropped

    return result


def _build_param_schema(param) -> dict:
    schema = _convert_schema(dict(param.json_schema))
    if param.description:
        schema["description"] = param.description
    return schema


def to_gemini(meta: FunctionMeta) -> dict:
    """Format a FunctionMeta as a Gemini FunctionDeclaration.

    Parameters
    ----------
    meta : FunctionMeta
        Intermediate representation from the inspector.

    Returns
    -------
    dict
        Ready to pass as an element of the ``tools[].function_declarations``
        list in the Gemini GenerativeModel API.

    Notes
    -----
    Gemini does not support ``anyOf`` / ``Union`` types in tool schemas.
    Optional parameters are handled by omitting them from the ``required``
    list rather than encoding nullability in the schema type.
    """
    properties: dict[str, dict] = {}
    required: list[str] = []

    for param in meta.params:
        properties[param.name] = _build_param_schema(param)
        if param.required:
            required.append(param.name)

    parameters: dict = {
        "type": "OBJECT",
        "properties": properties,
    }
    if required:
        parameters["required"] = required

    return {
        "name": meta.name,
        "description": meta.description,
        "parameters": parameters,
    }
