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
"""Unit tests for the file module."""

from raven.fathom.base import FileSize, FileSizeUnit
from raven.fathom.base import FileAccess, FilePermission

from tests.unit import TestCase


def noop(obj):
    """A function that ignores its argument and does nothing (NO-OP).

    Can be used to suppress linter warnings about unused expressions in tests.
    """


class TestFileSize(TestCase):
    """Tests for the `FileSize` and `FileSizeUnit` classes."""

    def test_create_file_size_with_float_value(self):
        size = FileSize(12.34, FileSizeUnit.KILOBYTE)
        self.assertEqual(size.value, 12.34)
        self.assertEqual(size.unit, FileSizeUnit.KILOBYTE)

    def test_create_file_size_with_int_value(self):
        size = FileSize(345, FileSizeUnit.BYTE)
        self.assertEqual(size.value, 345)
        self.assertEqual(size.unit, FileSizeUnit.BYTE)

    def test_creating_file_size_with_invalid_value_type_raises_ex(self):
        with self.assertRaises(ValueError) as raised:
            FileSize("INVALID_FLOAT_VALUE", FileSizeUnit.BYTE) # type: ignore

        self.assertIn(
            "could not convert string to float",
            str(raised.exception)
        )

    def test_creating_file_size_with_invalid_unit_type_raises_ex(self):
        with self.assertRaises(TypeError) as raised:
            FileSize(345, "42") # type: ignore

        self.assertIn("Invalid argument", str(raised.exception))

    def test_can_get_file_size_unit_from_symbol_str(self):
        self.assertEqual(FileSizeUnit.with_symbol("B"), FileSizeUnit.BYTE)
        self.assertEqual(FileSizeUnit.with_symbol("KB"), FileSizeUnit.KILOBYTE)
        self.assertEqual(FileSizeUnit.with_symbol("KiB"), FileSizeUnit.KIBIBYTE)
        self.assertEqual(FileSizeUnit.with_symbol("MB"), FileSizeUnit.MEGABYTE)
        self.assertEqual(FileSizeUnit.with_symbol("MiB"), FileSizeUnit.MEBIBYTE)
        self.assertEqual(FileSizeUnit.with_symbol("GB"), FileSizeUnit.GIGABYTE)
        self.assertEqual(FileSizeUnit.with_symbol("GiB"), FileSizeUnit.GIBIBYTE)

    def test_getting_file_size_unit_with_invalid_symbol_raises_exception(self):
        with self.assertRaises(ValueError) as raised:
            FileSizeUnit.with_symbol("MA")

        self.assertIn("is not a valid file size unit", str(raised.exception))

    def test_get_size_in_bytes(self):
        size = FileSize(4, FileSizeUnit.KILOBYTE)
        self.assertEqual(size.in_bytes(), 4_000)
        size = FileSize(4, FileSizeUnit.MEGABYTE)
        self.assertEqual(size.in_bytes(), 4_000_000)
        size = FileSize(5, FileSizeUnit.GIGABYTE)
        self.assertEqual(size.in_bytes(), 5_000_000_000)

    def test_size_unit_bases(self):
        self.assertTrue(FileSizeUnit.BYTE.has_base_ten())
        self.assertTrue(FileSizeUnit.KILOBYTE.has_base_ten())
        self.assertFalse(FileSizeUnit.KILOBYTE.has_base_two())
        self.assertTrue(FileSizeUnit.MEGABYTE.has_base_ten())
        self.assertFalse(FileSizeUnit.MEGABYTE.has_base_two())
        self.assertTrue(FileSizeUnit.GIGABYTE.has_base_ten())
        self.assertFalse(FileSizeUnit.GIGABYTE.has_base_two())
        self.assertTrue(FileSizeUnit.BYTE.has_base_two())
        self.assertFalse(FileSizeUnit.KIBIBYTE.has_base_ten())
        self.assertTrue(FileSizeUnit.KIBIBYTE.has_base_two())
        self.assertFalse(FileSizeUnit.MEBIBYTE.has_base_ten())
        self.assertTrue(FileSizeUnit.MEBIBYTE.has_base_two())
        self.assertFalse(FileSizeUnit.GIBIBYTE.has_base_ten())
        self.assertTrue(FileSizeUnit.GIBIBYTE.has_base_two())

    def test_size_zero_bytes_as_human_readable(self):
        size = FileSize(0.0, FileSizeUnit.MEGABYTE)
        self.assertEqual(str(size.as_human_readable()), "0B")

    def test_size_in_bytes_as_human_readable(self):
        size = FileSize(0.512, FileSizeUnit.KILOBYTE)
        self.assertEqual(str(size.as_human_readable()), "512B")

    def test_size_in_kilobytes_as_human_readable(self):
        size = FileSize(0.5, FileSizeUnit.MEGABYTE)
        self.assertEqual(str(size.as_human_readable()), "500KB")

    def test_size_in_megabytes_as_human_readable(self):
        size = FileSize(0.5, FileSizeUnit.GIGABYTE)
        self.assertEqual(str(size.as_human_readable()), "500MB")

    def test_size_in_gigabytes_as_human_readable(self):
        size = FileSize(1.345, FileSizeUnit.GIGABYTE)
        self.assertEqual(str(size.as_human_readable()), "1.34GB")

    def test_converting_to_same_unit_with_rounding_does_round_result(self):
        size = FileSize(1.345, FileSizeUnit.GIGABYTE).with_unit(
            FileSizeUnit.GIGABYTE, rounding=1
        )
        self.assertEqual(str(size.as_human_readable()), "1.3GB")

    def test_conversions(self):
        value_to_test = 123
        for unit_under_test in FileSizeUnit:
            size = FileSize(value_to_test, unit_under_test)
            for conversion_unit in FileSizeUnit:
                if conversion_unit != unit_under_test:
                    size = size.with_unit(conversion_unit)

            # Convert back to original unit
            size = size.with_unit(unit_under_test, rounding=4)
            self.assertEqual(size.value, value_to_test)
            self.assertEqual(size.unit, unit_under_test)

    def test_from_string_value_with_bytes(self):
        size = FileSize.from_string_value("24")
        self.assertEqual(size.value, 24)
        self.assertEqual(size.unit, FileSizeUnit.BYTE)

    def test_from_string_value_with_kilobytes(self):
        size = FileSize.from_string_value("1KB")
        self.assertEqual(size.value, 1)
        self.assertEqual(size.unit, FileSizeUnit.KILOBYTE)

    def test_from_string_value_with_megabytes(self):
        size = FileSize.from_string_value("2 MB")
        self.assertEqual(size.value, 2)
        self.assertEqual(size.unit, FileSizeUnit.MEGABYTE)

    def test_from_string_value_with_spaces(self):
        size = FileSize.from_string_value(" 3 GB")
        self.assertEqual(size.value, 3)
        self.assertEqual(size.unit, FileSizeUnit.GIGABYTE)

    def test_from_string_value_with_decimal_and_kibibyte(self):
        size = FileSize.from_string_value("4.59KiB ")
        self.assertEqual(size.value, 4.59)
        self.assertEqual(size.unit, FileSizeUnit.KIBIBYTE)

    def test_from_string_value_with_lowercase_units(self):
        size = FileSize.from_string_value("  5.5 MiB  ")
        self.assertEqual(size.value, 5.5)
        self.assertEqual(size.unit, FileSizeUnit.MEBIBYTE)

    def test_from_string_value_with_invalid_format_raises(self):
        with self.assertRaises(ValueError) as raised:
            FileSize.from_string_value("not_a_size")

        self.assertIn("Invalid file size format", str(raised.exception))

    def test_from_string_value_with_invalid_unit_raises(self):
        with self.assertRaises(ValueError) as raised:
            FileSize.from_string_value("10XY")

        self.assertIn("is not a valid file size unit", str(raised.exception))

    def test_with_symbol_case_insensitive_lowercase(self):
        self.assertEqual(FileSizeUnit.with_symbol("kb"), FileSizeUnit.KILOBYTE)
        self.assertEqual(FileSizeUnit.with_symbol("mb"), FileSizeUnit.MEGABYTE)
        self.assertEqual(FileSizeUnit.with_symbol("gb"), FileSizeUnit.GIGABYTE)
        self.assertEqual(FileSizeUnit.with_symbol("b"), FileSizeUnit.BYTE)

    def test_with_symbol_case_insensitive_mixed_case(self):
        self.assertEqual(FileSizeUnit.with_symbol("Kb"), FileSizeUnit.KILOBYTE)
        self.assertEqual(FileSizeUnit.with_symbol("kB"), FileSizeUnit.KILOBYTE)
        self.assertEqual(FileSizeUnit.with_symbol("Mb"), FileSizeUnit.MEGABYTE)
        self.assertEqual(FileSizeUnit.with_symbol("mB"), FileSizeUnit.MEGABYTE)
        self.assertEqual(FileSizeUnit.with_symbol("Gb"), FileSizeUnit.GIGABYTE)
        self.assertEqual(FileSizeUnit.with_symbol("gB"), FileSizeUnit.GIGABYTE)

    def test_with_symbol_case_insensitive_binary_units(self):
        self.assertEqual(FileSizeUnit.with_symbol("kib"), FileSizeUnit.KIBIBYTE)
        self.assertEqual(FileSizeUnit.with_symbol("KIB"), FileSizeUnit.KIBIBYTE)
        self.assertEqual(FileSizeUnit.with_symbol("mib"), FileSizeUnit.MEBIBYTE)
        self.assertEqual(FileSizeUnit.with_symbol("MIB"), FileSizeUnit.MEBIBYTE)
        self.assertEqual(FileSizeUnit.with_symbol("gib"), FileSizeUnit.GIBIBYTE)
        self.assertEqual(FileSizeUnit.with_symbol("GIB"), FileSizeUnit.GIBIBYTE)

    def test_file_size_equality_same_unit(self):
        a = FileSize(100, FileSizeUnit.KILOBYTE)
        b = FileSize(100, FileSizeUnit.KILOBYTE)
        self.assertEqual(a, b)

    def test_file_size_equality_different_units_same_bytes(self):
        a = FileSize(1, FileSizeUnit.KILOBYTE)
        b = FileSize(1000, FileSizeUnit.BYTE)
        self.assertEqual(a, b)

    def test_file_size_inequality(self):
        a = FileSize(1, FileSizeUnit.KILOBYTE)
        b = FileSize(2, FileSizeUnit.KILOBYTE)
        self.assertNotEqual(a, b)

    def test_file_size_not_equal_to_non_file_size(self):
        a = FileSize(100, FileSizeUnit.BYTE)
        with self.assertRaises(TypeError):
            noop(a == 100)
        with self.assertRaises(TypeError):
            noop(a == "100B")

    def test_file_size_hash_equal_for_equal_sizes(self):
        a = FileSize(1, FileSizeUnit.KILOBYTE)
        b = FileSize(1000, FileSizeUnit.BYTE)
        self.assertEqual(hash(a), hash(b))

    def test_file_size_usable_in_set(self):
        a = FileSize(1, FileSizeUnit.KILOBYTE)
        b = FileSize(1000, FileSizeUnit.BYTE)
        c = FileSize(2, FileSizeUnit.KILOBYTE)
        s = {a, b, c}
        self.assertEqual(len(s), 2)


class TestFileAccess(TestCase):
    """Tests for the FileAccess class."""

    def test_file_access_equality_same_values(self):
        a = FileAccess((True, False, True))
        b = FileAccess((True, False, True))
        self.assertEqual(a, b)

    def test_file_access_inequality(self):
        a = FileAccess((True, False, True))
        b = FileAccess((True, True, True))
        self.assertNotEqual(a, b)

    def test_file_access_not_equal_to_non_file_access(self):
        a = FileAccess((True, False, False))
        with self.assertRaises(TypeError):
            noop(a == "rwx")
        with self.assertRaises(TypeError):
            noop(a == 42)

    def test_file_access_hash_equal_for_equal_values(self):
        a = FileAccess((True, True, False))
        b = FileAccess((True, True, False))
        self.assertEqual(hash(a), hash(b))

    def test_file_access_hash_different_for_different_values(self):
        a = FileAccess((True, True, False))
        b = FileAccess((True, False, False))
        self.assertNotEqual(hash(a), hash(b))

    def test_file_access_usable_in_set(self):
        a = FileAccess((True, False, False))
        b = FileAccess((True, False, False))
        c = FileAccess((False, True, False))
        s = {a, b, c}
        self.assertEqual(len(s), 2)


class TestFilePermission(TestCase):
    """Tests for the FilePermission class."""

    def test_file_permission_equality_same_values(self):
        owner = FileAccess((True, True, False))
        group = FileAccess((True, False, False))
        other = FileAccess((True, False, False))
        a = FilePermission((owner, group, other))
        b = FilePermission((owner, group, other))
        self.assertEqual(a, b)

    def test_file_permission_inequality(self):
        owner1 = FileAccess((True, True, False))
        owner2 = FileAccess((True, False, False))
        group = FileAccess((True, False, False))
        other = FileAccess((True, False, False))
        a = FilePermission((owner1, group, other))
        b = FilePermission((owner2, group, other))
        self.assertNotEqual(a, b)

    def test_file_permission_not_equal_to_non_file_permission(self):
        owner = FileAccess((True, True, False))
        group = FileAccess((True, False, False))
        other = FileAccess((True, False, False))
        a = FilePermission((owner, group, other))
        with self.assertRaises(TypeError):
            noop(a == "rw-r--r--")
        with self.assertRaises(TypeError):
            noop(a == 644)

    def test_file_permission_hash_equal_for_equal_values(self):
        owner = FileAccess((True, True, False))
        group = FileAccess((True, False, False))
        other = FileAccess((True, False, False))
        a = FilePermission((owner, group, other))
        b = FilePermission((owner, group, other))
        self.assertEqual(hash(a), hash(b))

    def test_file_permission_usable_in_set(self):
        owner = FileAccess((True, True, False))
        group = FileAccess((True, False, False))
        other = FileAccess((True, False, False))
        a = FilePermission((owner, group, other))
        b = FilePermission((owner, group, other))
        s = {a, b}
        self.assertEqual(len(s), 1)


if __name__ == "__main__":
    TestCase.run_tests()
