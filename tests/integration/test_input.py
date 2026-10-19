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

    def test_secret_input_uses_configured_stream(self):
        self.set_in("secret-value")
        captured_input = self.input_prompt.read("Password: ", secret=True)

        self.assertIsInstance(captured_input, str)
        self.assertEqual(captured_input, "secret-value")
        self.assert_output_contains("Password: ")

    def test_validator_accepts_valid_input(self):
        valid_input = "valid"
        self.set_in(valid_input)
        validator = lambda x: x == "valid"
        captured = self.input_prompt.read(validator=validator)
        self.assertEqual(captured, valid_input)

    def test_validator_rejects_invalid_input_and_accepts_on_retry(self):
        self.set_in("invalid\nvalid")
        def validator(x):
            if x == "valid":
                return True

            self.stream_out.write("Invalid input\n")
            return False

        captured = self.input_prompt.read(validator=validator)
        self.assertEqual(captured, "valid")
        self.assert_output_contains("Invalid input")

    def test_validator_with_default_value_validates_default(self):
        default_value = "default123"
        validator = lambda x: len(x) > 5
        captured = self.input_prompt.read(
            default_value=default_value,
            validator=validator
        )
        self.assertEqual(captured, default_value)

    def test_validator_rejects_default_value_and_accepts_user_input(self):
        self.set_in("toolong")
        default_value = "bad"  # too short
        validator = lambda x: len(x) > 5
        captured = self.input_prompt.read(
            default_value=default_value,
            validator=validator
        )
        self.assertEqual(captured, "toolong")

    def test_validator_with_prompt_repeats_prompt_on_invalid(self):
        self.set_in("invalid\nvalid")
        prompt = "Enter valid input: "
        validator = lambda x: x == "valid"
        captured = self.input_prompt.read(prompt, validator=validator)
        self.assertEqual(captured, "valid")
        self.assert_output_contains(prompt)

    def test_validator_numeric_input(self):
        self.set_in("123")
        validator = lambda x: x.isdigit()
        captured = self.input_prompt.read(validator=validator)
        self.assertEqual(captured, "123")

    def test_validator_rejects_non_numeric_and_accepts_numeric(self):
        self.set_in("abc\n456")
        validator = lambda x: x.isdigit()
        captured = self.input_prompt.read(validator=validator)
        self.assertEqual(captured, "456")

    def test_validator_with_secret_input(self):
        self.set_in("validpass")
        validator = lambda x: len(x) > 5
        captured = self.input_prompt.read(secret=True, validator=validator)
        self.assertEqual(captured, "validpass")

    def test_validator_rejects_secret_input_and_retries(self):
        self.set_in("short\nvalidsecret")
        def validator(x):
            if len(x) > 7:
                return True

            self.stream_out.write("Invalid input\n")
            return False

        captured = self.input_prompt.read(secret=True, validator=validator)
        self.assertEqual(captured, "validsecret")
        self.assert_output_contains("Invalid input")

    def test_validator_multiple_retries_until_valid(self):
        self.set_in("a\nbb\nccc\nvalid")
        def validator(x):
            if len(x) >= 5:
                return True

            self.stream_out.write("Invalid input\n")
            return False

        captured = self.input_prompt.read(validator=validator)
        self.assertEqual(captured, "valid")
        output = self.stream_out.getvalue()
        invalid_count = output.count("Invalid input")
        self.assertEqual(invalid_count, 3)

    def test_validator_with_empty_string_validation(self):
        default_value = ""
        validator = lambda x: True  # Always valid
        captured = self.input_prompt.read(
            default_value=default_value,
            validator=validator
        )
        self.assertEqual(captured, "")

    def test_select_returns_option_by_number(self):
        options = ["Option 1", "Option 2", "Option 3"]
        test_input = "2"
        self.set_in(test_input)
        captured = self.input_prompt.select(options)
        self.assertEqual(captured, "Option 2")
        self.assert_output_contains("[1] Option 1")
        self.assert_output_contains("[2] Option 2")
        self.assert_output_contains("[3] Option 3")

    def test_select_returns_option_by_name(self):
        options = ["Option 1", "Option 2", "Option 3"]
        test_input = "Option 1"
        self.set_in(test_input)
        captured = self.input_prompt.select(options)
        self.assertEqual(captured, "Option 1")
        self.assert_output_contains("[1] Option 1")
        self.assert_output_contains("[2] Option 2")
        self.assert_output_contains("[3] Option 3")

    def test_select_repeats_on_empty_input(self):
        options = ["Option 1", "Option 2"]
        test_input = "\n\n\nOption 2"
        self.set_in(test_input)
        captured = self.input_prompt.select(options, prompt="SENTINEL")
        self.assertEqual(captured, "Option 2")
        self.assertEqual(
            self.stream_out.getvalue().count("SENTINEL"),
            4,
            "Should have printed the prompt four times"
        )
        self.assertEqual(
            self.stream_out.getvalue().count("[1] Option 1"),
            1,
            "Should have printed the available options once"
        )

    def test_select_repeats_on_invalid_input(self):
        options = ["Option 1", "Option 2"]
        test_input = "invalid\nOption 1"
        self.set_in(test_input)
        captured = self.input_prompt.select(options, "Choose an option: ")
        self.assertEqual(captured, "Option 1")
        self.assertEqual(
            self.stream_out.getvalue().count("Choose an option: "),
            2
        )
        self.assertEqual(
            self.stream_out.getvalue().count("[1] Option 1"),
            1
        )

    def test_select_raises_value_error_on_empty_options(self):
        empty_sequence = []
        with self.assertRaises(ValueError) as raised:
            self.input_prompt.select(options=empty_sequence)

        self.assertIn(
            "The options sequence must not be empty",
            str(raised.exception)
        )

    def test_select_returns_default_value_on_empty_input(self):
        options = ["Option 1", "Option 2"]
        test_input = "\n"
        self.set_in(test_input)
        captured = self.input_prompt.select(options, default_value="DEFAULT")
        self.assertEqual(captured, "DEFAULT")

    def test_select_returns_default_value_on_whitespace_input(self):
        options = ["Option 1", "Option 2"]
        test_input = "   \n"
        self.set_in(test_input)
        captured = self.input_prompt.select(options, default_value="DEFAULT")
        self.assertEqual(captured, "DEFAULT")


if __name__ == "__main__":
    TestCase.run_tests()
