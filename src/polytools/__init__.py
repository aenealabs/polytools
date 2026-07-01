"""
polytools — Cross-provider LLM tool schema generation from Python type hints.

Zero external dependencies. Pure Python stdlib (inspect, typing, re, functools).
Requires Python 3.9+.

Quick start
-----------
::

    from polytools import tool

    @tool
    def search_web(query: str, max_results: int = 5) -> list[str]:
        '''Search the web and return relevant URLs.

        Args:
            query: The search query string.
            max_results: Maximum number of results to return.

        Returns:
            List of URLs matching the query.
        '''
        # your implementation here
        ...

    # Export to any provider:
    search_web.to_openai()     # OpenAI Chat Completions tools format
    search_web.to_anthropic()  # Anthropic Messages API tools format
    search_web.to_gemini()     # Gemini FunctionDeclaration format
    search_web.to_mcp()        # MCP JSON-RPC tool definition
    search_web.to_all()        # All four at once — dict keyed by provider

    # Invoke from an LLM's argument dict (works with any provider's response):
    search_web.call({"query": "latest Python releases"})

Supported type annotations
--------------------------
- Primitives: str, int, float, bool, bytes, None
- Generics:   list[T], dict[K, V], tuple[T, ...], set[T]
- Typing:     List, Dict, Tuple, Set, FrozenSet (typing module aliases)
- Optional:   Optional[T]  →  anyOf: [T_schema, null]
- Union:      Union[T1, T2]  →  anyOf: [T1_schema, T2_schema]
- Literal:    Literal["a", "b"]  →  {type: string, enum: ["a", "b"]}
- Any:        Any  →  {} (no constraints)

Docstring styles
----------------
Google, NumPy, and reStructuredText docstrings are all auto-detected and
parsed to extract per-parameter descriptions.
"""

from importlib.metadata import PackageNotFoundError, version as _version

from ._decorator import Tool, tool

__all__ = ["tool", "Tool"]

try:
    __version__ = _version("polytools")
except PackageNotFoundError:  # running from a source tree without install metadata
    __version__ = "0.0.0"
