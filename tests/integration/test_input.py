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
"""Integration tests for the _input module."""

from io import StringIO

from raven.fathom.base._input import SystemInputPromptStdIn

from tests.integration import TestCase


class TestSystemInputPromptStdIn(TestCase):
    """Integration tests for the `SystemInputPromptStdIn` class."""

    def setUp(self):
        super().setUp()
        self.input_prompt = SystemInputPromptStdIn()
        self.stream_in = StringIO()
        self.stream_out = StringIO()
        self.input_prompt.stream_in = self.stream_in
        self.input_prompt.stream_out = self.stream_out

    def set_in(self, data: str):
        """Sets the input stream to the given data."""
        self.stream_in.write(data + "\n")
        self.stream_in.seek(0)

    def assert_output_contains(self, expected_output: str):
        """Asserts that the output stream contains the expected output."""
        self.stream_out.seek(0)
        self.assertIn(expected_output, self.stream_out.getvalue())

    def test_can_retrieve_input_from_stdin(self):
        test_input = "The test input data"
        self.set_in(test_input)
        captured_input = self.input_prompt.read()
        self.assertIsInstance(captured_input, str)
        self.assertEqual(captured_input, test_input)

    def test_can_retrieve_input_from_stdin_with_prompt(self):
        test_input = "The test input data"
        test_prompt = "Please enter some input: "
        self.set_in(test_input)
        captured_input = self.input_prompt.read(test_prompt)

        self.assertIsInstance(captured_input, str)
        self.assertEqual(captured_input, test_input)
        self.assert_output_contains(test_prompt)

    def test_input_with_default_value(self):
        default_input = "DEFAULT INPUT"
        captured_input = self.input_prompt.read(default_value=default_input)
        self.assertIsInstance(captured_input, str)
        self.assertEqual(captured_input, default_input)

    def test_input_with_prompt_and_default_value(self):
        prompt = "Give input or press enter to use a default value: "
        default_input = "DEFAULT VALUE"
        captured_input = self.input_prompt.read(prompt, default_input)
        self.assertIsInstance(captured_input, str)
        self.assertEqual(captured_input, default_input)
        self.assert_output_contains(prompt)

    def test_trailing_newline_is_stripped_from_input(self):
        self.set_in("some value")
        captured = self.input_prompt.read()
        self.assertIsInstance(captured, str)
        self.assertFalse(
            captured.endswith("\n"),
            "Trailing newline should have been stripped from input"
        )
        self.assertEqual(captured, "some value")

    def test_empty_input_without_default_returns_empty_string(self):
        self.set_in("")
        captured = self.input_prompt.read()
        self.assertIsInstance(captured, str)
        self.assertEqual(captured, "")

    def test_whitespace_only_input_without_default_returns_given_input(self):
        test_input = "   "
        self.set_in(test_input)
        captured = self.input_prompt.read()
        self.assertIsInstance(captured, str)
        self.assertEqual(captured, test_input)

    def test_whitespace_only_input_with_default_returns_given_input(self):
        test_input = "   "
        self.set_in(test_input)
        captured = self.input_prompt.read(default_value="FALLBACK")
        self.assertEqual(captured, test_input)

    def test_eof_on_empty_stdin_returns_empty_string_input(self):
        captured = self.input_prompt.read()
        self.assertIsInstance(captured, str)
        self.assertEqual(captured, "")

    def test_read_returns_str_type(self):
        self.set_in("hello")
        result = self.input_prompt.read()
        self.assertIsInstance(result, str)

    def test_only_first_line_of_multiline_input_is_consumed(self):
        self.set_in("first line\nsecond line\n")
        first = self.input_prompt.read()
        self.assertEqual(first, "first line")


if __name__ == "__main__":
    TestCase.run_tests()
