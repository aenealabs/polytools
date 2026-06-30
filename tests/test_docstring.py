"""
Tests for _docstring.py — Google / NumPy / RST docstring parsing.
"""

import sys
import unittest

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent / "src"))

from polytools._docstring import parse_docstring


class TestGoogleStyle(unittest.TestCase):

    def test_basic(self):
        doc = """
        Search the web and return URLs.

        Args:
            query (str): The search query.
            max_results (int): Max number of results.

        Returns:
            list: URLs.
        """
        result = parse_docstring(doc)
        self.assertEqual(result.summary, "Search the web and return URLs.")
        self.assertIn("query", result.params)
        self.assertIn("max_results", result.params)
        self.assertEqual(result.params["query"], "The search query.")
        self.assertEqual(result.params["max_results"], "Max number of results.")

    def test_no_type_in_args(self):
        doc = """
        Get weather.

        Args:
            location: City name.
            units: celsius or fahrenheit.
        """
        result = parse_docstring(doc)
        self.assertEqual(result.params["location"], "City name.")
        self.assertEqual(result.params["units"], "celsius or fahrenheit.")

    def test_multiline_description(self):
        doc = """
        Do something.

        Args:
            param1: First line of description.
                Second line of description.
        """
        result = parse_docstring(doc)
        self.assertIn("First line", result.params["param1"])
        self.assertIn("Second line", result.params["param1"])

    def test_arguments_alias(self):
        doc = """
        Summary.

        Arguments:
            x: The x value.
        """
        result = parse_docstring(doc)
        self.assertIn("x", result.params)

    def test_empty_docstring(self):
        result = parse_docstring("")
        self.assertEqual(result.summary, "")
        self.assertEqual(result.params, {})

    def test_none_docstring(self):
        result = parse_docstring(None)
        self.assertEqual(result.summary, "")
        self.assertEqual(result.params, {})


class TestNumPyStyle(unittest.TestCase):

    def test_basic(self):
        doc = """
        Compute the mean of an array.

        Parameters
        ----------
        values : list
            The input values.
        weights : list, optional
            Optional weights for each value.

        Returns
        -------
        float
            The weighted mean.
        """
        result = parse_docstring(doc)
        self.assertEqual(result.summary, "Compute the mean of an array.")
        self.assertIn("values", result.params)
        self.assertIn("weights", result.params)
        self.assertEqual(result.params["values"], "The input values.")
        self.assertIn("Optional weights", result.params["weights"])

    def test_no_type(self):
        doc = """
        Do something.

        Parameters
        ----------
        x
            The x coordinate.
        y
            The y coordinate.
        """
        result = parse_docstring(doc)
        self.assertIn("x", result.params)
        self.assertIn("y", result.params)


class TestRSTStyle(unittest.TestCase):

    def test_basic(self):
        doc = """
        Send an email.

        :param recipient: The email address of the recipient.
        :param subject: The subject line.
        :param body: The message body.
        :returns: True if sent successfully.
        """
        result = parse_docstring(doc)
        self.assertIn("recipient", result.params)
        self.assertIn("subject", result.params)
        self.assertIn("body", result.params)
        self.assertEqual(result.params["recipient"], "The email address of the recipient.")

    def test_typed_param(self):
        doc = """
        :param str name: The name.
        :param int age: The age.
        """
        result = parse_docstring(doc)
        self.assertIn("name", result.params)
        self.assertIn("age", result.params)


class TestSummaryOnly(unittest.TestCase):

    def test_summary_from_single_line(self):
        result = parse_docstring("Just a one-liner.")
        self.assertEqual(result.summary, "Just a one-liner.")

    def test_summary_from_multiline_first_paragraph(self):
        doc = """
        First paragraph
        continues here.

        Second paragraph.
        """
        result = parse_docstring(doc)
        self.assertIn("First paragraph", result.summary)
        self.assertIn("continues here", result.summary)

    def test_no_params_section(self):
        doc = "Do something useful with no parameters documented."
        result = parse_docstring(doc)
        self.assertEqual(result.params, {})
        self.assertEqual(result.summary, "Do something useful with no parameters documented.")


if __name__ == "__main__":
    unittest.main()
