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
"""Unit tests for the base _varchive module."""

from raven.fathom.base import ArchiveFileMember
from raven.fathom.base import ArchiveFileIO
from raven.fathom.base import File

from tests.unit import TestCase

# pylint: disable=C0103


class TestJsonArchiveFileIO(TestCase):
    """Unit tests for the `JsonArchiveFileIO` class."""

    def setUp(self):
        self.fs = File.get_file_system()
        self.fs.flush_system()
        self.io = ArchiveFileIO.instance()

    def assertMemberIsInList(self, member, member_list):
        """Asserts that the given archive file member is
        part of the given member list.
        """
        if not any(
            isinstance(m, ArchiveFileMember) and m.name == member.name
            for m in member_list
        ):
            raise AssertionError(
                f"No archive member '{member}' found in member list"
            )

    def prepare_archive_file(self):
        """Creates a prepared packed archive file."""
        path = "/testing/files/my-archive.zip"
        archive = File(path)
        archive.get_parent_directory().create_directory_tree()
        archive.write_all(
            '{"format": "JSON", '
            '"files": {"A": null, "B": null, "A/a": "414141", '
            '"A/b": "424242", "B/C": null, "B/C/d": "444444"}}'
        )
        return path

    def test_compress_to_archive(self):
        member_a = ArchiveFileMember("member_A", content=b"AAA")
        member_b = ArchiveFileMember("member_B", content=b"BBBB")
        member_c = ArchiveFileMember("member_C", content=b"CCCCC")
        members = [member_a, member_b, member_c]
        archive = File("/testing/my-archive.zip")
        self.assertFalse(archive.exists())
        self.io.compress(members, archive)
        self.assertTrue(archive.is_regular_file())
        expected_file_content = (
            '{"format": "JSON", '
            '"files": {"member_A": "414141", "member_B": "42424242", '
            '"member_C": "4343434343"}}'
        )
        self.assertEqual(archive.read_all_text(), expected_file_content)

    def test_compress_with_directories(self):
        dir_a = ArchiveFileMember("A")
        dir_b = ArchiveFileMember("B")
        dir_b_c = ArchiveFileMember("B/C")
        a_a = ArchiveFileMember("A/a", content=b"AAA")
        a_b = ArchiveFileMember("A/b", content=b"BBB")
        b_c_d = ArchiveFileMember("B/C/d", content=b"DDD")
        members = [dir_a, dir_b, a_a, a_b, dir_b_c, b_c_d]
        archive = File("/testing/files/archive_with_dirs.zip")
        self.assertFalse(archive.exists())
        self.io.compress(members, archive)
        self.assertTrue(archive.is_regular_file())
        expected_file_content = (
            '{"format": "JSON", '
            '"files": {"A": null, "B": null, "A/a": "414141", '
            '"A/b": "424242", "B/C": null, "B/C/d": "444444"}}'
        )
        self.assertEqual(archive.read_all_text(), expected_file_content)

    def test_extract_archive_to_directory(self):
        path = self.prepare_archive_file()
        archive = File(path)
        destination = File("/testing/files/target")
        self.io.extract(archive, destination)
        self.assertTrue(archive.is_regular_file())
        self.assertTrue(destination.is_directory())
        self.assertTrue((destination / "A").is_directory())
        self.assertTrue((destination / "B").is_directory())
        self.assertTrue((destination / "A/a").is_regular_file())
        self.assertEqual((destination / "A/a").read_all_text(), "AAA")
        self.assertTrue((destination / "A/b").is_regular_file())
        self.assertEqual((destination / "A/b").read_all_text(), "BBB")
        self.assertTrue((destination / "B/C").is_directory())
        self.assertTrue((destination / "B/C/d").is_regular_file())
        self.assertEqual((destination / "B/C/d").read_all_text(), "DDD")

    def test_read_packed_members_from_archive(self):
        path = self.prepare_archive_file()
        archive = File(path)
        members = self.io.read_packed_members(archive)
        self.assertIsInstance(members, list)
        self.assertEqual(len(members), 6)
        self.assertMemberIsInList(ArchiveFileMember("A"), members)
        self.assertMemberIsInList(ArchiveFileMember("B"), members)
        self.assertMemberIsInList(ArchiveFileMember("A/a"), members)
        self.assertMemberIsInList(ArchiveFileMember("A/b"), members)
        self.assertMemberIsInList(ArchiveFileMember("B/C"), members)
        self.assertMemberIsInList(ArchiveFileMember("B/C/d"), members)


if __name__ == "__main__":
    TestCase.run_tests()
