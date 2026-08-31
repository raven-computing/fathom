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
"""Unit tests for the base version module."""

from raven.fathom.base import read_version_string
from raven.fathom.base import read_version_file, write_version_file
from raven.fathom.base import VersionStruct
from raven.fathom.base import File

from tests.unit import TestCase


class TestVersionStruct(TestCase):
    """Tests for the `VersionStruct` class."""

    def test_can_create_struct(self):
        version = VersionStruct(1, 2, 3)
        self.assertEqual(version.major, 1)
        self.assertEqual(version.minor, 2)
        self.assertEqual(version.patch, 3)
        self.assertEqual(version.extension, "")

    def test_can_create_struct_with_extension(self):
        version = VersionStruct(1, 2, 3, "alpha")
        self.assertEqual(version.major, 1)
        self.assertEqual(version.minor, 2)
        self.assertEqual(version.patch, 3)
        self.assertEqual(version.extension, "alpha")

    def test_invalid_extension(self):
        with self.assertRaises(ValueError) as raised:
            VersionStruct(1, 2, 3, "invalid_extension!")

        self.assertIn("must be alphanumeric", str(raised.exception))

    def test_eq_operator(self):
        self.assertTrue(VersionStruct(0, 0, 1) == VersionStruct(0, 0, 1))
        self.assertTrue(VersionStruct(0, 2, 1) == VersionStruct(0, 2, 1))
        self.assertTrue(VersionStruct(1, 4, 3) == VersionStruct(1, 4, 3))
        self.assertTrue(
            VersionStruct(1, 2, 4, "alpha") == VersionStruct(1, 2, 4, "alpha")
        )
        self.assertTrue(
            VersionStruct(1, 0, 0, "beta") == VersionStruct(1, 0, 0, "alpha")
        )
        self.assertFalse(VersionStruct(1, 0, 0) == VersionStruct(1, 0, 1))
        self.assertFalse(VersionStruct(0, 0, 2) == VersionStruct(0, 0, 1))
        self.assertFalse(VersionStruct(1, 3, 1) == VersionStruct(1, 4, 1))
        self.assertFalse(VersionStruct(1, 0, 0) == VersionStruct(2, 0, 0))
        self.assertFalse(
            VersionStruct(1, 0, 0) == VersionStruct(1, 0, 0, "alpha")
        )

    def test_ne_operator(self):
        self.assertTrue(VersionStruct(1, 0, 0) != VersionStruct(1, 0, 1))
        self.assertTrue(VersionStruct(0, 0, 2) != VersionStruct(0, 0, 1))
        self.assertTrue(VersionStruct(1, 3, 1) != VersionStruct(1, 4, 1))
        self.assertTrue(VersionStruct(1, 0, 0) != VersionStruct(2, 0, 0))
        self.assertTrue(
            VersionStruct(1, 2, 4) != VersionStruct(1, 2, 4, "alpha")
        )
        self.assertTrue(
            VersionStruct(1, 0, 0, "beta") != VersionStruct(1, 0, 0)
        )
        self.assertFalse(VersionStruct(0, 0, 1) != VersionStruct(0, 0, 1))
        self.assertFalse(VersionStruct(0, 2, 1) != VersionStruct(0, 2, 1))
        self.assertFalse(VersionStruct(1, 4, 3) != VersionStruct(1, 4, 3))
        self.assertFalse(
            VersionStruct(1, 0, 0, "beta") != VersionStruct(1, 0, 0, "beta")
        )

    def test_lt_operator(self):
        self.assertTrue(VersionStruct(1, 0, 0) < VersionStruct(1, 0, 1))
        self.assertTrue(VersionStruct(1, 0, 8) < VersionStruct(1, 1, 3))
        self.assertTrue(VersionStruct(1, 9, 9) < VersionStruct(2, 0, 0))
        self.assertTrue(
            VersionStruct(1, 0, 0, "alpha") < VersionStruct(1, 0, 0)
        )
        self.assertFalse(VersionStruct(1, 0, 0) < VersionStruct(1, 0, 0))
        self.assertFalse(VersionStruct(2, 0, 0) < VersionStruct(1, 0, 1))
        self.assertFalse(VersionStruct(1, 6, 1) < VersionStruct(1, 4, 4))
        self.assertFalse(VersionStruct(0, 0, 3) < VersionStruct(0, 0, 2))
        self.assertFalse(
            VersionStruct(1, 3, 4) < VersionStruct(1, 3, 4, "alpha")
        )

    def test_le_operator(self):
        self.assertTrue(VersionStruct(1, 0, 0) <= VersionStruct(1, 0, 1))
        self.assertTrue(VersionStruct(1, 0, 8) <= VersionStruct(1, 1, 3))
        self.assertTrue(VersionStruct(1, 9, 9) <= VersionStruct(2, 0, 0))
        self.assertTrue(VersionStruct(1, 2, 3) <= VersionStruct(1, 2, 3))
        self.assertTrue(
            VersionStruct(1, 0, 0, "alpha") <= VersionStruct(1, 0, 0)
        )
        self.assertFalse(VersionStruct(2, 0, 0) <= VersionStruct(1, 0, 1))
        self.assertFalse(VersionStruct(1, 6, 1) <= VersionStruct(1, 4, 4))
        self.assertFalse(VersionStruct(0, 0, 3) <= VersionStruct(0, 0, 2))
        self.assertFalse(
            VersionStruct(1, 0, 0) <= VersionStruct(1, 0, 0, "alpha")
        )

    def test_gt_operator(self):
        self.assertTrue(VersionStruct(1, 0, 1) > VersionStruct(1, 0, 0))
        self.assertTrue(VersionStruct(1, 1, 3) > VersionStruct(1, 0, 2))
        self.assertTrue(VersionStruct(2, 0, 0) > VersionStruct(1, 9, 9))
        self.assertTrue(
            VersionStruct(3, 4, 56) > VersionStruct(3, 4, 56, "beta")
        )
        self.assertFalse(VersionStruct(1, 0, 0) > VersionStruct(1, 0, 0))
        self.assertFalse(VersionStruct(1, 0, 1) > VersionStruct(2, 0, 0))
        self.assertFalse(VersionStruct(1, 4, 4) > VersionStruct(1, 6, 1))
        self.assertFalse(VersionStruct(0, 0, 2) > VersionStruct(0, 0, 3))
        self.assertFalse(
            VersionStruct(3, 4, 56, "dev") > VersionStruct(3, 4, 56)
        )

    def test_ge_operator(self):
        self.assertTrue(VersionStruct(1, 0, 1) >= VersionStruct(1, 0, 0))
        self.assertTrue(VersionStruct(1, 1, 3) >= VersionStruct(1, 0, 2))
        self.assertTrue(VersionStruct(2, 0, 0) >= VersionStruct(1, 9, 9))
        self.assertTrue(VersionStruct(0, 3, 5) >= VersionStruct(0, 3, 5))
        self.assertTrue(VersionStruct(0, 1, 2) >= VersionStruct(0, 1, 2))
        self.assertFalse(VersionStruct(1, 0, 1) >= VersionStruct(2, 0, 0))
        self.assertFalse(VersionStruct(1, 4, 4) >= VersionStruct(1, 6, 1))
        self.assertFalse(VersionStruct(0, 0, 2) >= VersionStruct(0, 0, 3))
        self.assertFalse(
            VersionStruct(0, 0, 2, "dev") >= VersionStruct(0, 0, 2)
        )

    def test_is_development_version(self):
        self.assertTrue(VersionStruct(1, 0, 0, "dev").is_development_version())
        self.assertFalse(VersionStruct(1, 0, 0).is_development_version())
        self.assertFalse(
            VersionStruct(1, 0, 0, "alpha").is_development_version()
        )

    def test_read_version_string(self):
        version = read_version_string("1.2.3")
        assert version is not None
        self.assertEqual(version.major, 1)
        self.assertEqual(version.minor, 2)
        self.assertEqual(version.patch, 3)
        self.assertEqual(version.extension, "")

        version = read_version_string("1.2.3-alpha")
        assert version is not None
        self.assertEqual(version.major, 1)
        self.assertEqual(version.minor, 2)
        self.assertEqual(version.patch, 3)
        self.assertEqual(version.extension, "alpha")

        self.assertIsNone(read_version_string("invalid_version"))

    def test_read_write_version_file(self):
        directory = File("/tmp/test-directory")
        directory.create_directory_tree()
        version = VersionStruct(2, 3, 4, "beta")
        write_version_file(directory, version)

        re_read = read_version_file(directory)
        self.assertIsNotNone(re_read)
        self.assertEqual(re_read, version)

        version_file = directory / "VERSION"
        version_file.write_all("")
        empty_read = read_version_file(directory)
        self.assertIsNone(empty_read)

        version_file.remove()
        empty_directory_read = read_version_file(directory)
        self.assertIsNone(empty_directory_read)


if __name__ == "__main__":
    TestCase.run_tests()
