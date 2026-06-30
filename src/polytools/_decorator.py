"""
The @tool decorator and Tool wrapper class.

Tool wraps a Python callable and lazily computes provider schemas on demand.
Schemas are cached after the first call — inspection runs at most once per Tool.
"""

from __future__ import annotations

import functools
from typing import Any, Callable, Optional, overload

from ._inspector import inspect_function
from ._types import FunctionMeta


class Tool:
    """A Python function decorated with ``@tool``.

    Calling a ``Tool`` instance behaves identically to calling the original
    function. The additional provider-schema methods are available as attributes.

    Attributes
    ----------
    __wrapped__ : Callable
        The original unwrapped function.

    Examples
    --------
    ::

        @tool
        def get_weather(location: str, units: str = "celsius") -> dict:
            '''Get current weather for a location.

            Args:
                location: City name or coordinates.
                units: Temperature units, either 'celsius' or 'fahrenheit'.
            '''
            ...

        get_weather.to_openai()     # OpenAI function calling format
        get_weather.to_anthropic()  # Anthropic tools format
        get_weather.to_gemini()     # Gemini function declarations
        get_weather.to_mcp()        # MCP JSON-RPC tool definition
        get_weather.to_all()        # All four at once
        get_weather.call({"location": "Paris"})  # invoke with LLM arg dict
    """

    __slots__ = ("__wrapped__", "_meta_cache", "__dict__")

    def __init__(self, func: Callable) -> None:
        self.__wrapped__ = func
        self._meta_cache: Optional[FunctionMeta] = None
        # Copy over __name__, __doc__, __module__, __qualname__, __annotations__
        functools.update_wrapper(self, func)

    # ------------------------------------------------------------------
    # Transparent call-through
    # ------------------------------------------------------------------

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Call the underlying function normally."""
        return self.__wrapped__(*args, **kwargs)

    def __repr__(self) -> str:
        return f"Tool({self.__wrapped__!r})"

    # ------------------------------------------------------------------
    # Lazy metadata resolution
    # ------------------------------------------------------------------

    @property
    def _meta(self) -> FunctionMeta:
        """FunctionMeta, computed once and cached."""
        if self._meta_cache is None:
            self._meta_cache = inspect_function(self.__wrapped__)
        return self._meta_cache

    # ------------------------------------------------------------------
    # Provider formatters
    # ------------------------------------------------------------------

    def to_openai(self) -> dict:
        """Return the OpenAI function-calling schema for this tool.

        Returns
        -------
        dict
            Suitable for the ``tools`` parameter of the OpenAI Chat
            Completions API (``client.chat.completions.create(tools=[...])``)
        """
        from ._providers._openai import to_openai
        return to_openai(self._meta)

    def to_anthropic(self) -> dict:
        """Return the Anthropic tool-use schema for this tool.

        Returns
        -------
        dict
            Suitable for the ``tools`` parameter of the Anthropic Messages
            API (``client.messages.create(tools=[...])``)
        """
        from ._providers._anthropic import to_anthropic
        return to_anthropic(self._meta)

    def to_gemini(self) -> dict:
        """Return the Gemini FunctionDeclaration schema for this tool.

        Returns
        -------
        dict
            Suitable for a ``tools[].function_declarations`` element in the
            Gemini GenerativeModel API.

        Notes
        -----
        Gemini does not support ``anyOf`` / ``Union`` types. Optional
        parameters are handled by exclusion from the ``required`` list.
        """
        from ._providers._gemini import to_gemini
        return to_gemini(self._meta)

    def to_mcp(self) -> dict:
        """Return the MCP tool definition for this tool.

        Returns
        -------
        dict
            Suitable as an element of the ``tools`` list in an MCP
            ``tools/list`` JSON-RPC response.
        """
        from ._providers._mcp import to_mcp
        return to_mcp(self._meta)

    def to_all(self) -> dict[str, dict]:
        """Return schemas for all four providers at once.

        Returns
        -------
        dict
            Keys: ``"openai"``, ``"anthropic"``, ``"gemini"``, ``"mcp"``.
            Each value is the provider-specific schema dict.

        Examples
        --------
        ::

            schemas = my_tool.to_all()
            # Pass to whichever provider you're using today:
            openai_client.chat.completions.create(
                tools=[schemas["openai"]], ...
            )
        """
        return {
            "openai":    self.to_openai(),
            "anthropic": self.to_anthropic(),
            "gemini":    self.to_gemini(),
            "mcp":       self.to_mcp(),
        }

    # ------------------------------------------------------------------
    # Invocation helper
    # ------------------------------------------------------------------

    def call(self, arguments: dict[str, Any]) -> Any:
        """Invoke the underlying function with a dict of arguments.

        This is the bridge between what an LLM returns (a JSON object of
        arguments) and the actual Python function call.

        Parameters
        ----------
        arguments : dict
            Keyword arguments as a dict, e.g. the ``arguments`` field from
            an OpenAI tool-call response or Anthropic tool-use block.

        Returns
        -------
        Any
            Whatever the underlying function returns.

        Examples
        --------
        ::

            # OpenAI response handling
            tool_call = response.choices[0].message.tool_calls[0]
            import json
            result = my_tool.call(json.loads(tool_call.function.arguments))

            # Anthropic response handling
            block = response.content[0]  # ToolUseBlock
            result = my_tool.call(block.input)
        """
        return self.__wrapped__(**arguments)


# ---------------------------------------------------------------------------
# Decorator factory
# ---------------------------------------------------------------------------

@overload
def tool(func: Callable) -> Tool: ...

@overload
def tool(func: None = None) -> Callable[[Callable], Tool]: ...


def tool(func: Optional[Callable] = None) -> "Tool | Callable[[Callable], Tool]":
    """Decorator that converts a Python function into a cross-provider LLM tool.

    Can be used with or without parentheses::

        @tool
        def my_func(x: int) -> str: ...

        @tool()
        def my_func(x: int) -> str: ...

    Parameters
    ----------
    func : Callable, optional
        The function to wrap. When ``@tool`` is used without parentheses,
        this is the decorated function. When used as ``@tool()``, this is
        ``None`` and a decorator is returned.

    Returns
    -------
    Tool | Callable[[Callable], Tool]
        A ``Tool`` instance (when called with a function) or a decorator
        (when called without arguments).
    """
    if func is not None:
        return Tool(func)

    def decorator(f: Callable) -> Tool:
        return Tool(f)

    return decorator
