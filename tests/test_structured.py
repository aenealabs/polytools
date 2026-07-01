"""Structured-input support: Enum, dataclass, TypedDict, NamedTuple → object schemas."""

import enum
import unittest
from dataclasses import dataclass, field
from typing import Dict, List, NamedTuple, Optional, TypedDict

from polytools import tool
from polytools._schema import annotation_to_schema


# ---- Fixtures (module level so forward refs resolve) --------------------
class Color(enum.Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"


class Priority(enum.IntEnum):
    LOW = 1
    HIGH = 2


@dataclass
class Address:
    street: str
    city: str
    zip_code: str = ""


@dataclass
class Person:
    name: str
    age: int
    address: Address
    nicknames: List[str] = field(default_factory=list)


class Movie(TypedDict):
    title: str
    year: int


class PartialConfig(TypedDict, total=False):
    verbose: str
    retries: int


class Coord(NamedTuple):
    x: int
    y: int
    label: str = "origin"


@dataclass
class Node:
    value: int
    next: Optional["Node"] = None  # self-referential


# ---- Enums --------------------------------------------------------------
class TestEnum(unittest.TestCase):
    def test_string_enum(self):
        self.assertEqual(
            annotation_to_schema(Color),
            {"type": "string", "enum": ["red", "green", "blue"]},
        )

    def test_int_enum(self):
        self.assertEqual(
            annotation_to_schema(Priority),
            {"type": "integer", "enum": [1, 2]},
        )


# ---- Dataclasses --------------------------------------------------------
class TestDataclass(unittest.TestCase):
    def test_flat_dataclass(self):
        schema = annotation_to_schema(Address)
        self.assertEqual(schema["type"], "object")
        self.assertEqual(set(schema["properties"]), {"street", "city", "zip_code"})
        self.assertEqual(schema["properties"]["street"], {"type": "string"})
        # zip_code has a default → not required
        self.assertEqual(schema["required"], ["street", "city"])

    def test_nested_dataclass(self):
        schema = annotation_to_schema(Person)
        props = schema["properties"]
        self.assertEqual(props["address"]["type"], "object")
        self.assertEqual(props["address"]["properties"]["city"], {"type": "string"})
        self.assertEqual(props["nicknames"], {"type": "array", "items": {"type": "string"}})
        # nicknames has default_factory → not required
        self.assertEqual(schema["required"], ["name", "age", "address"])

    def test_self_referential_does_not_recurse_infinitely(self):
        schema = annotation_to_schema(Node)
        self.assertEqual(schema["type"], "object")
        # The recursive 'next' field collapses to a bare object.
        self.assertIn("next", schema["properties"])
        self.assertEqual(schema["properties"]["value"], {"type": "integer"})


# ---- TypedDict ----------------------------------------------------------
class TestTypedDict(unittest.TestCase):
    def test_total_typeddict_all_required(self):
        schema = annotation_to_schema(Movie)
        self.assertEqual(schema["type"], "object")
        self.assertEqual(set(schema["properties"]), {"title", "year"})
        self.assertEqual(sorted(schema["required"]), ["title", "year"])

    def test_partial_typeddict_none_required(self):
        schema = annotation_to_schema(PartialConfig)
        self.assertEqual(set(schema["properties"]), {"verbose", "retries"})
        self.assertNotIn("required", schema)


# ---- NamedTuple ---------------------------------------------------------
class TestNamedTuple(unittest.TestCase):
    def test_namedtuple_as_object(self):
        schema = annotation_to_schema(Coord)
        self.assertEqual(schema["type"], "object")
        self.assertEqual(schema["properties"]["x"], {"type": "integer"})
        # label has a default → not required
        self.assertEqual(schema["required"], ["x", "y"])


# ---- Nested combinations ------------------------------------------------
class TestNested(unittest.TestCase):
    def test_list_of_dataclass(self):
        schema = annotation_to_schema(List[Address])
        self.assertEqual(schema["type"], "array")
        self.assertEqual(schema["items"]["type"], "object")
        self.assertIn("street", schema["items"]["properties"])

    def test_optional_dataclass(self):
        schema = annotation_to_schema(Optional[Address])
        self.assertEqual(schema["anyOf"][0]["type"], "object")
        self.assertEqual(schema["anyOf"][1], {"type": "null"})

    def test_dict_of_enum(self):
        schema = annotation_to_schema(Dict[str, Color])
        self.assertEqual(schema["type"], "object")
        self.assertEqual(
            schema["additionalProperties"], {"type": "string", "enum": ["red", "green", "blue"]}
        )


# ---- Provider integration ----------------------------------------------
class TestProviders(unittest.TestCase):
    def setUp(self):
        @tool
        def create_user(person: Person, color: Color) -> bool:
            """Create a user.

            Args:
                person: The person to create.
                color: Favorite color.
            """
            return True

        self.tool = create_user

    def test_openai_embeds_nested_object(self):
        params = self.tool.to_openai()["function"]["parameters"]
        person = params["properties"]["person"]
        self.assertEqual(person["type"], "object")
        self.assertEqual(person["properties"]["address"]["type"], "object")
        self.assertEqual(person["required"], ["name", "age", "address"])
        self.assertEqual(params["properties"]["color"]["enum"], ["red", "green", "blue"])
        self.assertEqual(params["required"], ["person", "color"])

    def test_anthropic_and_mcp_pass_nested_through(self):
        for schema, key in (
            (self.tool.to_anthropic(), "input_schema"),
            (self.tool.to_mcp(), "inputSchema"),
        ):
            props = schema[key]["properties"]
            self.assertEqual(props["person"]["type"], "object")
            self.assertEqual(props["person"]["required"], ["name", "age", "address"])

    def test_gemini_uppercases_and_preserves_nested_required(self):
        gparams = self.tool.to_gemini()["parameters"]
        person = gparams["properties"]["person"]
        self.assertEqual(person["type"], "OBJECT")
        self.assertEqual(person["properties"]["address"]["type"], "OBJECT")
        self.assertEqual(person["properties"]["address"]["properties"]["street"]["type"], "STRING")
        # The nested-required fix: required survives Gemini conversion.
        self.assertEqual(person["required"], ["name", "age", "address"])
        self.assertEqual(gparams["properties"]["color"]["type"], "STRING")

    def test_description_still_merged_on_structured_param(self):
        person = self.tool.to_openai()["function"]["parameters"]["properties"]["person"]
        self.assertEqual(person["description"], "The person to create.")


if __name__ == "__main__":
    unittest.main()
