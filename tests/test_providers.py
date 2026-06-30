"""
End-to-end tests for all four provider formatters.

Each test defines a function with type hints + a Google-style docstring,
decorates it with @tool, and asserts the exact expected schema for each
provider.
"""

import sys
import unittest
from typing import Literal, Optional

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent / "src"))

from polytools import tool, Tool


# ---------------------------------------------------------------------------
# Sample tools used across tests
# ---------------------------------------------------------------------------

@tool
def search_web(query: str, max_results: int = 5) -> list[str]:
    """Search the web and return relevant URLs.

    Args:
        query: The search query string.
        max_results: Maximum number of results to return.
    """
    ...


@tool
def send_email(
    recipient: str,
    subject: str,
    body: str,
    cc: Optional[str] = None,
) -> bool:
    """Send an email message.

    Args:
        recipient: Email address of the primary recipient.
        subject: Subject line of the email.
        body: Full text body of the email.
        cc: Optional CC email address.
    """
    ...


@tool
def set_sort_order(order: Literal["asc", "desc"]) -> None:
    """Set the sort direction.

    Args:
        order: Sort direction, either 'asc' or 'desc'.
    """
    ...


@tool
def no_annotations(query, limit=10):
    """A tool with no type annotations."""
    ...


@tool
def no_docstring(query: str, limit: int = 10) -> list[str]:
    pass


# ---------------------------------------------------------------------------
# Shared assertion helpers
# ---------------------------------------------------------------------------

def _get_props(schema: dict, provider: str) -> dict:
    """Extract the properties dict from a provider schema."""
    if provider == "openai":
        return schema["function"]["parameters"]["properties"]
    elif provider == "anthropic":
        return schema["input_schema"]["properties"]
    elif provider == "gemini":
        return schema["parameters"]["properties"]
    elif provider == "mcp":
        return schema["inputSchema"]["properties"]
    raise ValueError(provider)


def _get_required(schema: dict, provider: str) -> list:
    if provider == "openai":
        return schema["function"]["parameters"].get("required", [])
    elif provider == "anthropic":
        return schema["input_schema"].get("required", [])
    elif provider == "gemini":
        return schema["parameters"].get("required", [])
    elif provider == "mcp":
        return schema["inputSchema"].get("required", [])
    raise ValueError(provider)


# ---------------------------------------------------------------------------
# @tool decorator tests
# ---------------------------------------------------------------------------

class TestToolDecorator(unittest.TestCase):

    def test_returns_tool_instance(self):
        self.assertIsInstance(search_web, Tool)

    def test_callable(self):
        # Decorated function should still be callable
        # (our stubs use ... so they return None)
        result = search_web("python", max_results=3)
        self.assertIsNone(result)

    def test_preserves_name(self):
        self.assertEqual(search_web.__name__, "search_web")

    def test_preserves_doc(self):
        self.assertIn("Search the web", search_web.__doc__)

    def test_call_method(self):
        result = search_web.call({"query": "hello", "max_results": 2})
        self.assertIsNone(result)

    def test_to_all_keys(self):
        all_schemas = search_web.to_all()
        self.assertSetEqual(set(all_schemas.keys()), {"openai", "anthropic", "gemini", "mcp"})

    def test_meta_is_cached(self):
        # Accessing _meta twice should return the same object
        m1 = search_web._meta
        m2 = search_web._meta
        self.assertIs(m1, m2)

    def test_tool_without_parens(self):
        @tool
        def f(x: int) -> str: ...
        self.assertIsInstance(f, Tool)

    def test_tool_with_parens(self):
        @tool()
        def f(x: int) -> str: ...
        self.assertIsInstance(f, Tool)


# ---------------------------------------------------------------------------
# OpenAI provider
# ---------------------------------------------------------------------------

class TestOpenAI(unittest.TestCase):

    def setUp(self):
        self.schema = search_web.to_openai()

    def test_top_level_type(self):
        self.assertEqual(self.schema["type"], "function")

    def test_function_name(self):
        self.assertEqual(self.schema["function"]["name"], "search_web")

    def test_description(self):
        self.assertIn("Search the web", self.schema["function"]["description"])

    def test_query_required(self):
        required = _get_required(self.schema, "openai")
        self.assertIn("query", required)

    def test_max_results_not_required(self):
        required = _get_required(self.schema, "openai")
        self.assertNotIn("max_results", required)

    def test_query_type(self):
        props = _get_props(self.schema, "openai")
        self.assertEqual(props["query"]["type"], "string")

    def test_max_results_type(self):
        props = _get_props(self.schema, "openai")
        self.assertEqual(props["max_results"]["type"], "integer")

    def test_param_descriptions(self):
        props = _get_props(self.schema, "openai")
        self.assertIn("description", props["query"])
        self.assertIn("description", props["max_results"])

    def test_optional_param(self):
        schema = send_email.to_openai()
        required = _get_required(schema, "openai")
        self.assertNotIn("cc", required)
        props = _get_props(schema, "openai")
        self.assertIn("anyOf", props["cc"])

    def test_literal_enum(self):
        schema = set_sort_order.to_openai()
        props = _get_props(schema, "openai")
        self.assertEqual(props["order"]["type"], "string")
        self.assertEqual(set(props["order"]["enum"]), {"asc", "desc"})

    def test_no_annotations(self):
        # Should not raise; params with no annotation get {} schema
        schema = no_annotations.to_openai()
        self.assertIn("function", schema)

    def test_no_docstring(self):
        schema = no_docstring.to_openai()
        # Description should be empty string, not raise
        self.assertEqual(schema["function"]["description"], "")


# ---------------------------------------------------------------------------
# Anthropic provider
# ---------------------------------------------------------------------------

class TestAnthropic(unittest.TestCase):

    def setUp(self):
        self.schema = search_web.to_anthropic()

    def test_no_type_wrapper(self):
        self.assertNotIn("type", self.schema)

    def test_name(self):
        self.assertEqual(self.schema["name"], "search_web")

    def test_input_schema_key(self):
        self.assertIn("input_schema", self.schema)
        self.assertNotIn("parameters", self.schema)

    def test_input_schema_type(self):
        self.assertEqual(self.schema["input_schema"]["type"], "object")

    def test_query_required(self):
        required = _get_required(self.schema, "anthropic")
        self.assertIn("query", required)

    def test_max_results_optional(self):
        required = _get_required(self.schema, "anthropic")
        self.assertNotIn("max_results", required)

    def test_types(self):
        props = _get_props(self.schema, "anthropic")
        self.assertEqual(props["query"]["type"], "string")
        self.assertEqual(props["max_results"]["type"], "integer")

    def test_description_in_props(self):
        props = _get_props(self.schema, "anthropic")
        self.assertIn("description", props["query"])

    def test_optional_anyof(self):
        schema = send_email.to_anthropic()
        props = _get_props(schema, "anthropic")
        self.assertIn("anyOf", props["cc"])

    def test_literal(self):
        schema = set_sort_order.to_anthropic()
        props = _get_props(schema, "anthropic")
        self.assertEqual(props["order"]["type"], "string")
        self.assertIn("asc", props["order"]["enum"])


# ---------------------------------------------------------------------------
# Gemini provider
# ---------------------------------------------------------------------------

class TestGemini(unittest.TestCase):

    def setUp(self):
        self.schema = search_web.to_gemini()

    def test_name(self):
        self.assertEqual(self.schema["name"], "search_web")

    def test_parameters_key(self):
        self.assertIn("parameters", self.schema)

    def test_top_level_type_uppercase(self):
        self.assertEqual(self.schema["parameters"]["type"], "OBJECT")

    def test_string_type_uppercase(self):
        props = _get_props(self.schema, "gemini")
        self.assertEqual(props["query"]["type"], "STRING")

    def test_integer_type_uppercase(self):
        props = _get_props(self.schema, "gemini")
        self.assertEqual(props["max_results"]["type"], "INTEGER")

    def test_required_list(self):
        required = _get_required(self.schema, "gemini")
        self.assertIn("query", required)
        self.assertNotIn("max_results", required)

    def test_optional_not_in_required(self):
        # Gemini: Optional → not in required (no anyOf)
        schema = send_email.to_gemini()
        required = _get_required(schema, "gemini")
        self.assertNotIn("cc", required)
        # cc should still appear in properties with a STRING type
        props = _get_props(schema, "gemini")
        self.assertIn("cc", props)

    def test_literal_enum(self):
        schema = set_sort_order.to_gemini()
        props = _get_props(schema, "gemini")
        self.assertIn("enum", props["order"])
        self.assertEqual(set(props["order"]["enum"]), {"asc", "desc"})

    def test_list_type(self):
        @tool
        def f(items: list[str]) -> None: ...
        schema = f.to_gemini()
        props = _get_props(schema, "gemini")
        self.assertEqual(props["items"]["type"], "ARRAY")
        self.assertEqual(props["items"]["items"]["type"], "STRING")


# ---------------------------------------------------------------------------
# MCP provider
# ---------------------------------------------------------------------------

class TestMCP(unittest.TestCase):

    def setUp(self):
        self.schema = search_web.to_mcp()

    def test_name(self):
        self.assertEqual(self.schema["name"], "search_web")

    def test_input_schema_camelcase(self):
        self.assertIn("inputSchema", self.schema)
        self.assertNotIn("input_schema", self.schema)
        self.assertNotIn("parameters", self.schema)

    def test_input_schema_type(self):
        self.assertEqual(self.schema["inputSchema"]["type"], "object")

    def test_required(self):
        required = _get_required(self.schema, "mcp")
        self.assertIn("query", required)
        self.assertNotIn("max_results", required)

    def test_properties_types(self):
        props = _get_props(self.schema, "mcp")
        self.assertEqual(props["query"]["type"], "string")
        self.assertEqual(props["max_results"]["type"], "integer")

    def test_description_in_props(self):
        props = _get_props(self.schema, "mcp")
        self.assertIn("description", props["query"])

    def test_optional_anyof(self):
        schema = send_email.to_mcp()
        props = _get_props(schema, "mcp")
        self.assertIn("anyOf", props["cc"])

    def test_literal(self):
        schema = set_sort_order.to_mcp()
        props = _get_props(schema, "mcp")
        self.assertEqual(props["order"]["type"], "string")
        self.assertIn("asc", props["order"]["enum"])


# ---------------------------------------------------------------------------
# to_all()
# ---------------------------------------------------------------------------

class TestToAll(unittest.TestCase):

    def test_all_four_providers(self):
        all_s = search_web.to_all()
        self.assertIn("openai", all_s)
        self.assertIn("anthropic", all_s)
        self.assertIn("gemini", all_s)
        self.assertIn("mcp", all_s)

    def test_independent_dicts(self):
        # Mutating one should not affect another
        all_s = search_web.to_all()
        all_s["openai"]["injected"] = True
        self.assertNotIn("injected", all_s["anthropic"])


if __name__ == "__main__":
    unittest.main()
