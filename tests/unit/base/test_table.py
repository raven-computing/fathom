# Copyright (C) 2026 Raven Computing
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""Unit tests for the table formatting module."""

from raven.fathom.base import TableFormatter

from tests.unit import TestCase


class TestTableFormatter(TestCase):
    """Tests for the `TableFormatter` class."""

    def test_initializer_with_title(self):
        formatter = TableFormatter(title="Test Table")
        self.assertEqual(formatter.title, "Test Table")
        self.assertEqual(formatter.size(), 0)

    def test_initializer_without_title(self):
        formatter = TableFormatter()
        self.assertIsNone(formatter.title)

    def test_set_headers_returns_self(self):
        formatter = TableFormatter()
        result = formatter.set_headers("Col1", "Col2", "Col3")
        self.assertIs(result, formatter)

    def test_add_row_returns_self(self):
        formatter = TableFormatter()
        result = formatter.add_row("val1", "val2", "val3")
        self.assertIs(result, formatter)
        size = formatter.size()
        self.assertEqual(size, 1)

    def test_add_row_converts_values_to_strings(self):
        formatter = TableFormatter()
        formatter.add_row(1, True, None)
        output = formatter.get_formatted_text()
        self.assertIn("1", output)
        self.assertIn("True", output)
        self.assertIn("None", output)

    def test_method_chaining(self):
        formatter = TableFormatter().set_headers(
            "A", "B"
        ).add_row(
            1, 2
        ).add_row(
            3, 4
        )
        size = formatter.size()
        self.assertEqual(size, 2)

    def test_format_with_no_data(self):
        formatter = TableFormatter(title="Empty")
        result = formatter.get_formatted_text()
        self.assertEqual(result, "Empty")

    def test_format_with_headers_and_rows(self):
        formatter = (
            TableFormatter(title="Users")
            .set_headers("Name", "Age")
            .add_row("Alice", 30)
            .add_row("Bob", 25)
        )
        result = formatter.get_formatted_text()
        self.assertIsInstance(result, str)
        self.assertIn("Users", result)
        self.assertIn("Name", result)
        self.assertIn("Alice", result)
        self.assertIn("30", result)
        self.assertIn("Bob", result)
        self.assertIn("25", result)

    def test_format_with_rows_no_headers(self):
        formatter = (
            TableFormatter(title="Data")
            .add_row("val1", "val2")
            .add_row("val3", "val4")
        )
        result = formatter.get_formatted_text()
        self.assertIsInstance(result, str)
        self.assertIn("Data", result)
        self.assertIn("val1", result)
        self.assertIn("val2", result)

    def test_size_method_returns_row_count(self):
        formatter = TableFormatter()
        size = formatter.size()
        self.assertEqual(size, 0)
        formatter.add_row("a", "b")
        size = formatter.size()
        self.assertEqual(size, 1)
        formatter.add_row("c", "d")
        size = formatter.size()
        self.assertEqual(size, 2)

    def test_complete_formatted_output(self):
        formatter = (
            TableFormatter(title="User Directory")
            .set_headers("ID", "Name", "Role")
            .add_row("001", "Alice", "admin")
            .add_row("002", "Bob", "user")
            .add_row("003", "Charlie", "moderator")
        )

        actual_output = formatter.get_formatted_text()

        expected_output = (
            "User Directory\n"
            " | ID  | Name    | Role     \n"
            "-+-----+---------+----------\n"
            " | 001 | Alice   | admin    \n"
            " | 002 | Bob     | user     \n"
            " | 003 | Charlie | moderator"
        )

        self.assertEqual(expected_output, actual_output)


if __name__ == "__main__":
    TestCase.run_tests()
