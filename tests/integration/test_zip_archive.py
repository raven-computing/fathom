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
"""Integration tests for the ZIP archive file I/O implementation."""

import zipfile

from raven.fathom.base import ArchiveFile, ArchiveFileIO
from raven.fathom.base import ArchiveFileIOException
from raven.fathom.base import File
from raven.fathom.base._zip import ZipArchiveFileIO

from tests.integration.archive_io import ArchiveFileIOTestCase


class TestZipArchiveFileIO(ArchiveFileIOTestCase):
    """Integration tests for the `ZipArchiveFileIO` class."""

    def setUp(self):
        super().setUp()
        self.io = ArchiveFileIO.instance(ArchiveFile.Format.ZIP)
        self.assertIsInstance(self.io, ZipArchiveFileIO)

    def test_compress_to_zip_archive(self):
        path = self.create_path("test-archive.zip")
        archive = File(path)
        self.assertFileDoesNotExist(path)
        self.io.compress(self.file_members, archive)
        self.assertFileExists(path)
        self.assertTrue(archive.is_regular_file())
        compressed_archive_bytes = archive.read_all_bytes()
        magic_bytes = compressed_archive_bytes[:4]
        self.assertEqual(magic_bytes, bytes.fromhex("504B0304"))

        check_directory = File(self.create_directory("check"))
        self.io.extract(archive, check_directory)
        self.assert_directory_equals_expected_extracted(check_directory)

    def test_extract_zip_archive_to_directory(self):
        archive = File(self.create_path("test-archive.zip"))
        self.io.compress(self.file_members, archive)
        self.assertFileExists(archive.path)

        extract_directory = File(self.create_directory("extracted"))
        self.io.extract(archive, extract_directory)
        self.assertFileExists(archive.path)
        self.assertDirectoryExists(extract_directory.path)
        self.assert_directory_equals_expected_extracted(extract_directory)

    def test_read_packed_members_from_zip_archive(self):
        archive = File(self.create_path("test-archive.zip"))
        self.io.compress(self.file_members, archive)
        self.assertFileExists(archive.path)

        packed_members = self.io.read_packed_members(archive)
        self.assertEqual(len(packed_members), 9)
        expected_memberset = {member.name for member in self.file_members}
        actual_memberset = {member.name for member in packed_members}
        self.assertEqual(actual_memberset, expected_memberset)

    def test_extract_zip_archive_rejects_path_traversal(self):
        archive_path = self.create_path("traversal.zip")
        with zipfile.ZipFile(archive_path, "w") as zip_file:
            zip_file.writestr("../escaped.txt", "escaped content")
        archive = File(archive_path)
        extract_dir = File(self.create_directory("extracted"))
        with self.assertRaises(ArchiveFileIOException):
            self.io.extract(archive, extract_dir)

    def test_extract_zip_archive_rejects_absolute_path_in_member(self):
        archive_path = self.create_path("absolute-path.zip")
        with zipfile.ZipFile(archive_path, "w") as zip_file:
            zip_file.writestr("/etc/escaped.txt", "escaped content")

        archive = File(archive_path)
        extract_dir = File(self.create_directory("extracted"))
        with self.assertRaises(ArchiveFileIOException) as raised:
            self.io.extract(archive, extract_dir)

        self.assertIn(
            "Archive member path would escape destination directory",
            str(raised.exception)
        )

    def test_compress_empty_member_list_produces_valid_zip_archive(self):
        path = self.create_path("empty.zip")
        archive = File(path)
        self.io.compress([], archive)
        self.assertFileExists(path)
        self.assertTrue(archive.is_regular_file())
        self.assertGreater(archive.size().value, 0)
        packed_members = self.io.read_packed_members(archive)
        self.assertEqual(len(packed_members), 0)


if __name__ == "__main__":
    ArchiveFileIOTestCase.run_tests()
