"""
Tests for _schema.py — Python type annotation → JSON Schema conversion.
"""

import sys
import unittest
from typing import Any, Dict, FrozenSet, List, Literal, Optional, Set, Tuple, Union

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent / "src"))

from polytools._schema import annotation_to_schema


class TestPrimitives(unittest.TestCase):

    def test_str(self):
        self.assertEqual(annotation_to_schema(str), {"type": "string"})

    def test_int(self):
        self.assertEqual(annotation_to_schema(int), {"type": "integer"})

    def test_float(self):
        self.assertEqual(annotation_to_schema(float), {"type": "number"})

    def test_bool(self):
        self.assertEqual(annotation_to_schema(bool), {"type": "boolean"})

    def test_bytes(self):
        self.assertEqual(annotation_to_schema(bytes), {"type": "string", "format": "byte"})

    def test_none_type(self):
        self.assertEqual(annotation_to_schema(type(None)), {"type": "null"})

    def test_any(self):
        self.assertEqual(annotation_to_schema(Any), {})

    def test_empty(self):
        import inspect
        self.assertEqual(annotation_to_schema(inspect.Parameter.empty), {})


class TestOptional(unittest.TestCase):

    def test_optional_str(self):
        result = annotation_to_schema(Optional[str])
        self.assertEqual(result, {"anyOf": [{"type": "string"}, {"type": "null"}]})

    def test_optional_int(self):
        result = annotation_to_schema(Optional[int])
        self.assertEqual(result, {"anyOf": [{"type": "integer"}, {"type": "null"}]})

    def test_optional_list(self):
        result = annotation_to_schema(Optional[List[str]])
        self.assertEqual(result, {
            "anyOf": [
                {"type": "array", "items": {"type": "string"}},
                {"type": "null"},
            ]
        })


class TestUnion(unittest.TestCase):

    def test_union_str_int(self):
        result = annotation_to_schema(Union[str, int])
        self.assertIn("anyOf", result)
        self.assertIn({"type": "string"}, result["anyOf"])
        self.assertIn({"type": "integer"}, result["anyOf"])

    def test_union_three_types(self):
        result = annotation_to_schema(Union[str, int, float])
        self.assertEqual(len(result["anyOf"]), 3)


class TestLiteral(unittest.TestCase):

    def test_literal_strings(self):
        result = annotation_to_schema(Literal["asc", "desc"])
        self.assertEqual(result, {"type": "string", "enum": ["asc", "desc"]})

    def test_literal_ints(self):
        result = annotation_to_schema(Literal[1, 2, 3])
        self.assertEqual(result, {"type": "integer", "enum": [1, 2, 3]})

    def test_literal_mixed(self):
        result = annotation_to_schema(Literal["a", 1])
        self.assertIn("enum", result)
        self.assertNotIn("type", result)  # mixed → bare enum


class TestList(unittest.TestCase):

    def test_bare_list(self):
        self.assertEqual(annotation_to_schema(list), {"type": "array"})

    def test_list_of_str(self):
        result = annotation_to_schema(List[str])
        self.assertEqual(result, {"type": "array", "items": {"type": "string"}})

    def test_list_of_list(self):
        result = annotation_to_schema(List[List[int]])
        self.assertEqual(result, {
            "type": "array",
            "items": {"type": "array", "items": {"type": "integer"}},
        })

    # Python 3.9+ built-in generics
    def test_list_builtin(self):
        result = annotation_to_schema(list[str])
        self.assertEqual(result, {"type": "array", "items": {"type": "string"}})


class TestDict(unittest.TestCase):

    def test_bare_dict(self):
        self.assertEqual(annotation_to_schema(dict), {"type": "object"})

    def test_dict_str_int(self):
        result = annotation_to_schema(Dict[str, int])
        self.assertEqual(result, {"type": "object", "additionalProperties": {"type": "integer"}})

    def test_dict_builtin(self):
        result = annotation_to_schema(dict[str, float])
        self.assertEqual(result, {"type": "object", "additionalProperties": {"type": "number"}})


class TestTuple(unittest.TestCase):

    def test_homogeneous_tuple(self):
        result = annotation_to_schema(Tuple[str, ...])
        self.assertEqual(result, {"type": "array", "items": {"type": "string"}})

    def test_fixed_tuple(self):
        result = annotation_to_schema(Tuple[str, int, float])
        self.assertIn("prefixItems", result)
        self.assertEqual(result["minItems"], 3)
        self.assertEqual(result["maxItems"], 3)


class TestSet(unittest.TestCase):

    def test_set_of_str(self):
        result = annotation_to_schema(Set[str])
        self.assertEqual(result, {"type": "array", "uniqueItems": True, "items": {"type": "string"}})

    def test_frozenset(self):
        result = annotation_to_schema(FrozenSet[int])
        self.assertEqual(result, {"type": "array", "uniqueItems": True, "items": {"type": "integer"}})


class TestMutation(unittest.TestCase):
    """Ensure annotation_to_schema never mutates shared primitive dicts."""

    def test_primitives_are_copies(self):
        a = annotation_to_schema(str)
        b = annotation_to_schema(str)
        a["extra"] = True
        self.assertNotIn("extra", annotation_to_schema(str))


if __name__ == "__main__":
    unittest.main()
