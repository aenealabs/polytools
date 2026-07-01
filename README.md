# polytools

[![PyPI](https://img.shields.io/pypi/v/polytools?color=blue)](https://pypi.org/project/polytools/)
[![Python](https://img.shields.io/pypi/pyversions/polytools)](https://pypi.org/project/polytools/)
[![CI](https://img.shields.io/github/actions/workflow/status/aenealabs/polytools/ci.yml?label=CI)](https://github.com/aenealabs/polytools/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Zero dependencies](https://img.shields.io/badge/dependencies-none-brightgreen)](pyproject.toml)

**Cross-provider LLM tool schema generation from Python type hints.**

Write your tool once. Export to OpenAI, Anthropic, Gemini, and MCP — no framework lock-in, no third-party dependencies.

```python
from polytools import tool

@tool
def search_web(query: str, max_results: int = 5) -> list[str]:
    """Search the web and return relevant URLs.

    Args:
        query: The search query string.
        max_results: Maximum number of results to return.
    """
    ...

search_web.to_openai()     # → OpenAI function calling format
search_web.to_anthropic()  # → Anthropic tools format
search_web.to_gemini()     # → Gemini FunctionDeclaration format
search_web.to_mcp()        # → MCP JSON-RPC tool definition
search_web.to_all()        # → all four at once
```

## Why polytools?

Every LLM provider uses a different JSON format for tool/function definitions. Today you either hand-write four separate schemas, lock into a framework that weighs megabytes, or wrestle Pydantic into every project.

polytools is a single decorator — pure Python stdlib, zero external dependencies — that reads your type hints and docstring once and outputs whatever format you need.

## Installation

```bash
pip install polytools
```

Requires Python 3.9+. No other dependencies, ever.

## Quick Start

```python
from polytools import tool
from typing import Optional, Literal

@tool
def send_email(
    recipient: str,
    subject: str,
    body: str,
    cc: Optional[str] = None,
    priority: Literal["low", "normal", "high"] = "normal",
) -> bool:
    """Send an email message.

    Args:
        recipient: Email address of the primary recipient.
        subject: Subject line of the email.
        body: Full text body of the email.
        cc: Optional CC email address.
        priority: Message priority level.
    """
    ...
```

### OpenAI

```python
import openai

client = openai.OpenAI()
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Send an email to alice@example.com"}],
    tools=[send_email.to_openai()],
)
```

<details>
<summary>Schema output</summary>

```json
{
  "type": "function",
  "function": {
    "name": "send_email",
    "description": "Send an email message.",
    "parameters": {
      "type": "object",
      "properties": {
        "recipient": {"type": "string", "description": "Email address of the primary recipient."},
        "subject":   {"type": "string", "description": "Subject line of the email."},
        "body":      {"type": "string", "description": "Full text body of the email."},
        "cc":        {"anyOf": [{"type": "string"}, {"type": "null"}], "description": "Optional CC email address."},
        "priority":  {"type": "string", "enum": ["low", "normal", "high"], "description": "Message priority level."}
      },
      "required": ["recipient", "subject", "body"]
    }
  }
}
```
</details>

### Anthropic

```python
import anthropic

client = anthropic.Anthropic()
response = client.messages.create(
    model="claude-sonnet-4-6",
    messages=[{"role": "user", "content": "Send an email to alice@example.com"}],
    tools=[send_email.to_anthropic()],
)
```

<details>
<summary>Schema output</summary>

```json
{
  "name": "send_email",
  "description": "Send an email message.",
  "input_schema": {
    "type": "object",
    "properties": {
      "recipient": {"type": "string", "description": "Email address of the primary recipient."},
      "subject":   {"type": "string", "description": "Subject line of the email."},
      "body":      {"type": "string", "description": "Full text body of the email."},
      "cc":        {"anyOf": [{"type": "string"}, {"type": "null"}], "description": "Optional CC email address."},
      "priority":  {"type": "string", "enum": ["low", "normal", "high"], "description": "Message priority level."}
    },
    "required": ["recipient", "subject", "body"]
  }
}
```
</details>

### Gemini

```python
import google.generativeai as genai

model = genai.GenerativeModel(
    model_name="gemini-1.5-pro",
    tools=[{"function_declarations": [send_email.to_gemini()]}],
)
```

<details>
<summary>Schema output</summary>

```json
{
  "name": "send_email",
  "description": "Send an email message.",
  "parameters": {
    "type": "OBJECT",
    "properties": {
      "recipient": {"type": "STRING", "description": "Email address of the primary recipient."},
      "subject":   {"type": "STRING", "description": "Subject line of the email."},
      "body":      {"type": "STRING", "description": "Full text body of the email."},
      "cc":        {"type": "STRING", "description": "Optional CC email address."},
      "priority":  {"type": "STRING", "enum": ["low", "normal", "high"], "description": "Message priority level."}
    },
    "required": ["recipient", "subject", "body"]
  }
}
```
</details>

### MCP

```python
# In your MCP server's tools/list handler:
tools = [send_email.to_mcp()]
```

<details>
<summary>Schema output</summary>

```json
{
  "name": "send_email",
  "description": "Send an email message.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "recipient": {"type": "string", "description": "Email address of the primary recipient."},
      "subject":   {"type": "string", "description": "Subject line of the email."},
      "body":      {"type": "string", "description": "Full text body of the email."},
      "cc":        {"anyOf": [{"type": "string"}, {"type": "null"}], "description": "Optional CC email address."},
      "priority":  {"type": "string", "enum": ["low", "normal", "high"], "description": "Message priority level."}
    },
    "required": ["recipient", "subject", "body"]
  }
}
```
</details>

### Invoking from an LLM response

```python
import json

# OpenAI
tool_call = response.choices[0].message.tool_calls[0]
result = send_email.call(json.loads(tool_call.function.arguments))

# Anthropic
block = response.content[0]  # ToolUseBlock
result = send_email.call(block.input)
```

## Supported Type Annotations

| Python type | JSON Schema output |
|---|---|
| `str` | `{"type": "string"}` |
| `int` | `{"type": "integer"}` |
| `float` | `{"type": "number"}` |
| `bool` | `{"type": "boolean"}` |
| `bytes` | `{"type": "string", "format": "byte"}` |
| `None` / `type(None)` | `{"type": "null"}` |
| `list` / `List[T]` / `list[T]` | `{"type": "array", "items": {...}}` |
| `dict` / `Dict[K, V]` / `dict[K, V]` | `{"type": "object", "additionalProperties": {...}}` |
| `tuple[T, ...]` | `{"type": "array", "items": {...}}` |
| `tuple[T1, T2, T3]` | `{"type": "array", "prefixItems": [...]}` |
| `set[T]` / `frozenset[T]` | `{"type": "array", "uniqueItems": true, "items": {...}}` |
| `Optional[T]` | `{"anyOf": [{...}, {"type": "null"}]}` |
| `Union[T1, T2]` | `{"anyOf": [{...}, {...}]}` |
| `Literal["a", "b"]` | `{"type": "string", "enum": ["a", "b"]}` |
| `Enum` subclass | `{"type": <value type>, "enum": [...]}` |
| `dataclass` | `{"type": "object", "properties": {...}, "required": [...]}` |
| `TypedDict` | `{"type": "object", "properties": {...}, "required": [...]}` |
| `NamedTuple` | `{"type": "object", "properties": {...}, "required": [...]}` |
| `Any` | `{}` (no constraints) |
| Unannotated | `{}` (no constraints) |

Nested types are fully supported: `list[dict[str, Optional[int]]]` works as expected.

## Structured inputs

Parameters typed as a `dataclass`, `TypedDict`, `NamedTuple`, or `Enum` become proper nested JSON Schema objects — no Pydantic required. A field is marked `required` unless it has a default (or is a `total=False` / `NotRequired` TypedDict key).

```python
from dataclasses import dataclass
from enum import Enum
from polytools import tool

class Priority(Enum):
    LOW = "low"
    HIGH = "high"

@dataclass
class Ticket:
    title: str
    priority: Priority
    assignee: str = ""

@tool
def create_ticket(ticket: Ticket) -> str:
    """Open a support ticket.

    Args:
        ticket: The ticket to create.
    """
    ...

create_ticket.to_openai()
```

<details>
<summary>Schema output (parameters)</summary>

```json
{
  "type": "object",
  "properties": {
    "ticket": {
      "type": "object",
      "description": "The ticket to create.",
      "properties": {
        "title":    {"type": "string"},
        "priority": {"type": "string", "enum": ["low", "high"]},
        "assignee": {"type": "string"}
      },
      "required": ["title", "priority"]
    }
  },
  "required": ["ticket"]
}
```
</details>

Nesting is recursive (a dataclass field that is itself a dataclass, `list[SomeDataclass]`, `Optional[SomeTypedDict]`, `dict[str, SomeEnum]`, …). Self-referential types are guarded and collapse to a bare `{"type": "object"}`.

> **Note:** `.call(args)` passes the LLM's argument dict straight to your function; it does **not** reconstruct dataclass/TypedDict instances from that dict. Schema generation and argument coercion are separate concerns — coercion may land in a future release.

## Docstring Styles

Parameter descriptions are parsed automatically from Google, NumPy, and reStructuredText docstrings:

**Google** (recommended)
```python
def f(x: int, y: str = "hello") -> bool:
    """Summary line.

    Args:
        x: Description of x.
        y: Description of y.
    """
```

**NumPy**
```python
def f(x: int, y: str = "hello") -> bool:
    """Summary line.

    Parameters
    ----------
    x : int
        Description of x.
    y : str, optional
        Description of y.
    """
```

**reStructuredText**
```python
def f(x: int, y: str = "hello") -> bool:
    """Summary line.

    :param x: Description of x.
    :param y: Description of y.
    """
```

## API Reference

### `@tool`

Decorator that wraps a Python function and exposes provider schema methods. Can be used with or without parentheses:

```python
@tool
def my_func(...): ...

@tool()
def my_func(...): ...
```

### `Tool` methods

| Method | Returns | Description |
|---|---|---|
| `.to_openai()` | `dict` | OpenAI Chat Completions `tools` list entry |
| `.to_anthropic()` | `dict` | Anthropic Messages API `tools` list entry |
| `.to_gemini()` | `dict` | Gemini `function_declarations` list entry |
| `.to_mcp()` | `dict` | MCP `tools/list` response entry |
| `.to_all()` | `dict[str, dict]` | All four, keyed by provider name |
| `.call(args: dict)` | `Any` | Invoke the function with an LLM argument dict |

### `Tool` attributes

| Attribute | Type | Description |
|---|---|---|
| `__wrapped__` | `Callable` | The original unwrapped function |
| `__name__` | `str` | Preserved from the original function |
| `__doc__` | `str` | Preserved from the original function |

## Notes on Gemini

Gemini's API does not support `anyOf` in tool schemas. `Optional[T]` parameters are handled by omitting them from the `required` list rather than encoding nullability in the schema type. `Union` types are resolved to the first non-null type.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT — see [LICENSE](LICENSE).

---

Part of the [aenealabs](https://github.com/aenealabs) AI agent toolkit.
