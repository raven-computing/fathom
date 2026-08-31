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
"""Integration tests for the `SystemRandomEntropySource` implementation."""

from raven.fathom.base import EntropySource
from raven.fathom.base._random import SystemRandomEntropySource

from tests.integration import TestCase


class TestSystemRandomEntropySource(TestCase):
    """Integration tests for the `SystemRandomEntropySource` class."""

    def test_default_implementation(self):
        entropy = EntropySource.instance()
        self.assertIsNotNone(entropy)
        self.assertIsInstance(
            entropy, SystemRandomEntropySource,
            "Implementation detail: The default implementation provided for "
            "the EntropySource interface was expected to "
            f"be SystemRandomEntropySource but found {type(entropy)}. "
            "This is unexpected and may have a security-related impact. "
            "If this implementation detail was indeed changed, then please "
            "confirm by adjusting the test case."
        )

    def test_default_implementation_is_random(self):
        entropy = EntropySource.instance()
        is_random = entropy.is_random()
        self.assertTrue(
            is_random is True,
            "Implementation detail: The default implementation provided for "
            "the EntropySource interface was expected to return True "
            "for a call to the is_random() method "
            f"but it returned {type(is_random)}. "
            "This is unexpected and may have a security-related impact. "
            "If this implementation detail was indeed changed, then please "
            "confirm by adjusting the test case."
        )

    def test_next_random_int32_number_is_int(self):
        rng = SystemRandomEntropySource()
        random_number = rng.get_next_int32()
        self.assertIsInstance(random_number, int)

    def test_next_random_int32_numbers_are_random(self):
        rng = SystemRandomEntropySource()
        number_1 = rng.get_next_int32()
        number_2 = rng.get_next_int32()
        number_3 = rng.get_next_int32()
        number_4 = rng.get_next_int32()
        number_list = list(set([number_1, number_2, number_3, number_4]))
        number_list.sort()
        self.assertEqual(
            number_list, sorted([number_1, number_2, number_3, number_4])
        )

    def test_choose_one_from_int_sequence_returns_int_from_sequence(self):
        rng = SystemRandomEntropySource()
        sequence = list(range(256))
        random_item = rng.choose_one(sequence)
        self.assertIsInstance(random_item, int)

    def test_choose_one_from_str_sequence_returns_str_from_sequence(self):
        rng = SystemRandomEntropySource()
        sequence = [f"i={i}" for i in range(256)]
        random_item = rng.choose_one(sequence)
        self.assertIsInstance(random_item, str)

    def test_choose_one_from_sequence_returns_random_item(self):
        rng = SystemRandomEntropySource()
        sequence = list(range(2_000_000))
        item_1 = rng.choose_one(sequence)
        item_2 = rng.choose_one(sequence)
        item_3 = rng.choose_one(sequence)
        item_4 = rng.choose_one(sequence)
        item_list = list(set([item_1, item_2, item_3, item_4]))
        item_list.sort()
        self.assertEqual(item_list, sorted([item_1, item_2, item_3, item_4]))

    def test_get_bytes_returns_bytes_type(self):
        rng = SystemRandomEntropySource()
        result = rng.get_bytes(16)
        self.assertIsInstance(result, bytes)

    def test_get_bytes_returns_requested_number_of_bytes(self):
        rng = SystemRandomEntropySource()
        for count in (1, 8, 16, 32, 64, 256):
            result = rng.get_bytes(count)
            self.assertEqual(
                len(result),
                count,
                f"Expected {count} bytes but got {len(result)}"
            )

    def test_get_bytes_returns_zero_bytes_when_count_is_zero(self):
        rng = SystemRandomEntropySource()
        result = rng.get_bytes(0)
        self.assertIsInstance(result, bytes)
        self.assertEqual(0, len(result))

    def test_get_bytes_produces_random_output(self):
        # Two independent calls are unlikely to produce the same output
        rng = SystemRandomEntropySource()
        result_1 = rng.get_bytes(32)
        result_2 = rng.get_bytes(32)
        self.assertNotEqual(
            result_1,
            result_2,
            "Expected two independent 32-byte random values to differ. "
            "This failure is likely a programming error but might indicate a "
            "problem with the underlying system's entropy source."
        )

    def test_next_random_int32_number_is_in_expected_range(self):
        rng = SystemRandomEntropySource()
        for _ in range(20):
            value = rng.get_next_int32()
            self.assertGreaterEqual(value, 0)
            self.assertLessEqual(value, 0xffff_ffff)

    def test_choose_one_from_single_item_sequence_returns_that_item(self):
        rng = SystemRandomEntropySource()
        self.assertEqual(rng.choose_one([42]), 42)
        self.assertEqual(rng.choose_one(["only"]), "only")

    def test_choose_one_from_empty_sequence_raises_index_error(self):
        # Choosing from an empty sequence is a programming error
        rng = SystemRandomEntropySource()
        with self.assertRaises(IndexError):
            rng.choose_one([])


if __name__ == "__main__":
    TestCase.run_tests()
