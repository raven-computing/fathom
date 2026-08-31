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
"""Unit tests for the crypt module."""

import string

from raven.fathom.base import SecretToken
from raven.fathom.base.testing import EntropySourceMock

from tests.unit import TestCase


class TestSecretToken(TestCase):
    """Unit tests for the `SecretToken` class."""

    def test_two_secret_tokens_generated_are_not_the_same(self):
        token_1 = SecretToken()
        EntropySourceMock.instance().choose_sequence_index += 1
        token_2 = SecretToken()
        self.assertNotEqual(token_1, token_2)

    def test_token_with_ascii_alphabet_only_contains_ascii_chars(self):
        token = SecretToken(alphabet=SecretToken.ALPHABET_ASCII).to_string()
        self.assertRegex(token, "^[a-zA-Z0-9]{32}$")

    def test_token_with_hex_alphabet_only_contains_hex_chars(self):
        token = SecretToken(alphabet=SecretToken.ALPHABET_HEX).to_string()
        self.assertRegex(token, "^[a-f0-9]{32}$")

    def test_token_with_octal_alphabet_only_contains_octal_chars(self):
        token = SecretToken(alphabet=SecretToken.ALPHABET_OCTAL).to_string()
        self.assertRegex(token, "^[0-7]{32}$")

    def test_token_with_binary_alphabet_only_contains_ones_and_zeros(self):
        token = SecretToken(alphabet=SecretToken.ALPHABET_BINARY).to_string()
        self.assertRegex(token, "^[0-1]{32}$")

    def test_token_with_block_size_greater_one_is_divided_into_blocks(self):
        token = SecretToken(
            alphabet=SecretToken.ALPHABET_HEX,
            blocks=4
        ).to_string()
        self.assertRegex(
            token, "^[a-f0-9]{8}-[a-f0-9]{8}-[a-f0-9]{8}-[a-f0-9]{8}$"
        )

    def test_token_with_block_delimiter(self):
        token = SecretToken(
            alphabet=SecretToken.ALPHABET_HEX,
            blocks=4,
            block_delimiter=":"
        ).to_string()
        self.assertRegex(
            token, "^[a-f0-9]{8}:[a-f0-9]{8}:[a-f0-9]{8}:[a-f0-9]{8}$"
        )

    def test_token_has_correct_default_length(self):
        token = SecretToken()
        token_str = token.to_string()
        self.assertEqual(len(token_str), SecretToken.DEFAULT_SIZE)

    def test_token_with_custom_size(self):
        for size in (1, 8, 16, 64, 128):
            token_str = SecretToken(size=size).to_string()
            self.assertEqual(
                len(token_str),
                size,
                f"Expected token length {size} but got {len(token_str)}"
            )

    def test_token_with_blocks_has_correct_format(self):
        token_str = SecretToken(size=32, blocks=4).to_string()
        parts = token_str.split("-")
        self.assertEqual(4, len(parts))
        for part in parts:
            self.assertEqual(8, len(part))
            self.assertRegex(part, "^[a-zA-Z0-9]{8}$")

    def test_token_with_custom_block_delimiter(self):
        token_str = SecretToken(
            size=16,
            blocks=2,
            block_delimiter="_"
        ).to_string()
        parts = token_str.split("_")
        self.assertEqual(2, len(parts))
        for part in parts:
            self.assertEqual(8, len(part))

    def test_token_size_not_divisible_by_blocks_raises_value_error(self):
        # size=10 cannot be evenly divided into 3 blocks
        with self.assertRaises(ValueError) as raised:
            SecretToken(size=10, blocks=3)

        self.assertIn("divisible", str(raised.exception))

    def test_token_to_string_returns_str(self):
        token = SecretToken()
        self.assertIsInstance(token.to_string(), str)

    def test_token_repr_equals_to_string(self):
        token = SecretToken()
        self.assertEqual(repr(token), token.to_string())

    def test_equal_tokens_compare_as_equal(self):
        token_a = SecretToken(
            alphabet=string.ascii_lowercase,
            size=4
        )
        self.assertEqual(token_a, token_a)

    def test_token_is_hashable(self):
        token = SecretToken()
        token_set = {token}
        self.assertIn(token, token_set)
        self.assertEqual(1, len(token_set))

    def test_equal_tokens_have_equal_hash(self):
        token = SecretToken()
        # Same instance must yield the same hash on repeated calls
        self.assertEqual(hash(token), hash(token))


if __name__ == "__main__":
    TestCase.run_tests()
