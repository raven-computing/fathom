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
"""Integration tests for the TAR archive file I/O implementations."""

import io
import tarfile

from raven.fathom.base import ArchiveFile, ArchiveFileIO
from raven.fathom.base import ArchiveFileIOException
from raven.fathom.base import File
from raven.fathom.base._tar import TarArchiveFileIO, TarGzArchiveFileIO
from raven.fathom.base._tar import TarBzip2ArchiveFileIO, TarXzArchiveFileIO

from tests.integration import skipIfNotZlibAvailable
from tests.integration import skipIfNotBz2Available
from tests.integration import skipIfNotLzmaAvailable
from tests.integration.archive_io import ArchiveFileIOTestCase


class TestTarArchiveFileIO(ArchiveFileIOTestCase):
    """Integration tests for the `TarArchiveFileIO` class."""

    def setUp(self):
        super().setUp()
        self.io = ArchiveFileIO.instance(ArchiveFile.Format.TAR)
        self.assertIsInstance(self.io, TarArchiveFileIO)

    def test_compress_to_tar_archive(self):
        path = self.create_path("test-archive.tar")
        archive = File(path)
        self.assertFileDoesNotExist(path)
        self.io.compress(self.file_members, archive)
        self.assertFileExists(path)
        self.assertTrue(archive.is_regular_file())
        compressed_archive_bytes = archive.read_all_bytes()
        # PAX uses the header structure of the ustar format
        magic_bytes = compressed_archive_bytes[257:257+5]
        # non-null-terminated 'ustar' string
        ustar_header_magic = bytes.fromhex("7573746172")
        self.assertEqual(magic_bytes, ustar_header_magic)
        check_directory = File(self.create_directory("check"))
        self.io.extract(archive, check_directory)
        self.assert_directory_equals_expected_extracted(check_directory)

    def test_extract_tar_archive_to_directory(self):
        archive = File(self.create_path("test-archive.tar"))
        self.io.compress(self.file_members, archive)
        self.assertFileExists(archive.path)

        extract_directory = File(self.create_directory("extracted"))
        self.io.extract(archive, extract_directory)
        self.assertFileExists(archive.path)
        self.assertDirectoryExists(extract_directory.path)
        self.assert_directory_equals_expected_extracted(extract_directory)

    def test_read_packed_members_from_tar_archive(self):
        archive = File(self.create_path("test-archive.tar"))
        self.io.compress(self.file_members, archive)
        self.assertFileExists(archive.path)

        packed_members = self.io.read_packed_members(archive)
        self.assertEqual(len(packed_members), 9)
        expected_memberset = {member.name for member in self.file_members}
        actual_memberset = {member.name for member in packed_members}
        self.assertEqual(actual_memberset, expected_memberset)

    def test_extract_tar_archive_rejects_path_traversal(self):
        archive_path = self.create_path("traversal.tar")
        with tarfile.open(archive_path, "w") as tar_file:
            info = tarfile.TarInfo(name="../escaped.txt")
            data = b"escaped content"
            info.size = len(data)
            tar_file.addfile(info, io.BytesIO(data))
        archive = File(archive_path)
        extract_dir = File(self.create_directory("extracted"))
        with self.assertRaises(ArchiveFileIOException):
            self.io.extract(archive, extract_dir)

    def test_extract_tar_archive_rejects_absolute_path_in_member(self):
        archive_path = self.create_path("absolute-path.tar")
        with tarfile.open(archive_path, "w") as tar_file:
            info = tarfile.TarInfo(name="/etc/escaped.txt")
            data = b"escaped content"
            info.size = len(data)
            tar_file.addfile(info, io.BytesIO(data))

        archive = File(archive_path)
        extract_dir = File(self.create_directory("extracted"))
        with self.assertRaises(ArchiveFileIOException) as raised:
            self.io.extract(archive, extract_dir)

        self.assertIn(
            "Archive member path would escape destination directory",
            str(raised.exception)
        )

    def test_compress_empty_member_list_produces_valid_archive(self):
        path = self.create_path("empty.tar")
        archive = File(path)
        self.io.compress([], archive)
        self.assertFileExists(path)
        self.assertTrue(archive.is_regular_file())
        packed_members = self.io.read_packed_members(archive)
        self.assertEqual(len(packed_members), 0)


class TestTarGzArchiveFileIO(ArchiveFileIOTestCase):
    """Integration tests for the `TarGzArchiveFileIO` class."""

    def setUp(self):
        super().setUp()
        self.io = ArchiveFileIO.instance(ArchiveFile.Format.TAR_GZ)
        self.assertIsInstance(self.io, TarGzArchiveFileIO)

    @skipIfNotZlibAvailable()
    def test_compress_to_tar_gz_archive(self):
        path = self.create_path("test-archive.tar.gz")
        archive = File(path)
        self.assertFileDoesNotExist(path)
        self.io.compress(self.file_members, archive)
        self.assertFileExists(path)
        self.assertTrue(archive.is_regular_file())
        compressed_archive_bytes = archive.read_all_bytes()
        magic_bytes = compressed_archive_bytes[:2]
        gzip_tar_magic_bytes = bytes.fromhex("1f8b")
        self.assertEqual(magic_bytes, gzip_tar_magic_bytes)
        check_directory = File(self.create_directory("check"))
        self.io.extract(archive, check_directory)
        self.assert_directory_equals_expected_extracted(check_directory)

    @skipIfNotZlibAvailable()
    def test_extract_tar_gz_archive_to_directory(self):
        archive = File(self.create_path("test-archive.tar.gz"))
        self.io.compress(self.file_members, archive)
        self.assertFileExists(archive.path)

        extract_directory = File(self.create_directory("extracted"))
        self.io.extract(archive, extract_directory)
        self.assertFileExists(archive.path)
        self.assertDirectoryExists(extract_directory.path)
        self.assert_directory_equals_expected_extracted(extract_directory)

    @skipIfNotZlibAvailable()
    def test_read_packed_members_from_tar_gz_archive(self):
        archive = File(self.create_path("test-archive.tar.gz"))
        self.io.compress(self.file_members, archive)
        self.assertFileExists(archive.path)

        packed_members = self.io.read_packed_members(archive)
        self.assertEqual(len(packed_members), 9)
        expected_memberset = {member.name for member in self.file_members}
        actual_memberset = {member.name for member in packed_members}
        self.assertEqual(actual_memberset, expected_memberset)

    @skipIfNotZlibAvailable()
    def test_extract_tar_gz_archive_rejects_path_traversal(self):
        archive_path = self.create_path("traversal.tar.gz")
        with tarfile.open(archive_path, "w:gz") as tar_file:
            info = tarfile.TarInfo(name="../escaped.txt")
            data = b"escaped content"
            info.size = len(data)
            tar_file.addfile(info, io.BytesIO(data))

        archive = File(archive_path)
        extract_dir = File(self.create_directory("extracted"))
        with self.assertRaises(ArchiveFileIOException) as raised:
            self.io.extract(archive, extract_dir)

        self.assertIn(
            "Archive member path would escape destination directory",
            str(raised.exception)
        )

    @skipIfNotZlibAvailable()
    def test_extract_tar_gz_archive_rejects_absolute_path_in_member(self):
        archive_path = self.create_path("absolute-path.tar.gz")
        with tarfile.open(archive_path, "w:gz") as tar_file:
            info = tarfile.TarInfo(name="/etc/escaped.txt")
            data = b"escaped content"
            info.size = len(data)
            tar_file.addfile(info, io.BytesIO(data))

        archive = File(archive_path)
        extract_dir = File(self.create_directory("extracted"))
        with self.assertRaises(ArchiveFileIOException) as raised:
            self.io.extract(archive, extract_dir)

        self.assertIn(
            "Archive member path would escape destination directory",
            str(raised.exception)
        )

    @skipIfNotZlibAvailable()
    def test_compress_empty_member_list_produces_valid_tar_gz_archive(self):
        path = self.create_path("empty.tar.gz")
        archive = File(path)
        self.io.compress([], archive)
        self.assertFileExists(path)
        self.assertTrue(archive.is_regular_file())
        packed_members = self.io.read_packed_members(archive)
        self.assertEqual(len(packed_members), 0)


class TestTarBzip2ArchiveFileIO(ArchiveFileIOTestCase):
    """Integration tests for the `TarBzip2ArchiveFileIO` class."""

    def setUp(self):
        super().setUp()
        self.io = ArchiveFileIO.instance(ArchiveFile.Format.TAR_BZIP2)
        self.assertIsInstance(self.io, TarBzip2ArchiveFileIO)

    @skipIfNotBz2Available()
    def test_compress_to_tar_bzip2_archive(self):
        path = self.create_path("test-archive.tar.bz2")
        archive = File(path)
        self.assertFileDoesNotExist(path)
        self.io.compress(self.file_members, archive)
        self.assertFileExists(path)
        self.assertTrue(archive.is_regular_file())
        compressed_archive_bytes = archive.read_all_bytes()
        magic_bytes = compressed_archive_bytes[:3]
        bzip2_tar_magic_bytes = bytes.fromhex("425a68")
        self.assertEqual(magic_bytes, bzip2_tar_magic_bytes)
        check_directory = File(self.create_directory("check"))
        self.io.extract(archive, check_directory)
        self.assert_directory_equals_expected_extracted(check_directory)

    @skipIfNotBz2Available()
    def test_extract_tar_bzip2_archive_to_directory(self):
        archive = File(self.create_path("test-archive.tar.bz2"))
        self.io.compress(self.file_members, archive)
        self.assertFileExists(archive.path)

        extract_directory = File(self.create_directory("extracted"))
        self.io.extract(archive, extract_directory)
        self.assertFileExists(archive.path)
        self.assertDirectoryExists(extract_directory.path)
        self.assert_directory_equals_expected_extracted(extract_directory)

    @skipIfNotBz2Available()
    def test_read_packed_members_from_tar_bzip2_archive(self):
        archive = File(self.create_path("test-archive.tar.bz2"))
        self.io.compress(self.file_members, archive)
        self.assertFileExists(archive.path)

        packed_members = self.io.read_packed_members(archive)
        self.assertEqual(len(packed_members), 9)
        expected_memberset = {member.name for member in self.file_members}
        actual_memberset = {member.name for member in packed_members}
        self.assertEqual(actual_memberset, expected_memberset)

    @skipIfNotBz2Available()
    def test_extract_tar_bzip2_archive_rejects_path_traversal(self):
        archive_path = self.create_path("traversal.tar.bz2")
        with tarfile.open(archive_path, "w:bz2") as tar_file:
            info = tarfile.TarInfo(name="../escaped.txt")
            data = b"escaped content"
            info.size = len(data)
            tar_file.addfile(info, io.BytesIO(data))

        archive = File(archive_path)
        extract_dir = File(self.create_directory("extracted"))
        with self.assertRaises(ArchiveFileIOException) as raised:
            self.io.extract(archive, extract_dir)

        self.assertIn(
            "Archive member path would escape destination directory",
            str(raised.exception)
        )

    @skipIfNotBz2Available()
    def test_extract_tar_bzip2_archive_rejects_absolute_path_in_member(self):
        archive_path = self.create_path("absolute-path.tar.bz2")
        with tarfile.open(archive_path, "w:bz2") as tar_file:
            info = tarfile.TarInfo(name="/etc/escaped.txt")
            data = b"escaped content"
            info.size = len(data)
            tar_file.addfile(info, io.BytesIO(data))

        archive = File(archive_path)
        extract_dir = File(self.create_directory("extracted"))
        with self.assertRaises(ArchiveFileIOException) as raised:
            self.io.extract(archive, extract_dir)

        self.assertIn(
            "Archive member path would escape destination directory",
            str(raised.exception)
        )

    @skipIfNotBz2Available()
    def test_compress_empty_member_list_produces_valid_tar_bzip2_archive(self):
        path = self.create_path("empty.tar.bz2")
        archive = File(path)
        self.io.compress([], archive)
        self.assertFileExists(path)
        self.assertTrue(archive.is_regular_file())
        packed_members = self.io.read_packed_members(archive)
        self.assertEqual(len(packed_members), 0)


class TestTarXzArchiveFileIO(ArchiveFileIOTestCase):
    """Integration tests for the `TarXzArchiveFileIO` class."""

    def setUp(self):
        super().setUp()
        self.io = ArchiveFileIO.instance(ArchiveFile.Format.TAR_XZ)
        self.assertIsInstance(self.io, TarXzArchiveFileIO)

    @skipIfNotLzmaAvailable()
    def test_compress_to_tar_xz_archive(self):
        path = self.create_path("test-archive.tar.xz")
        archive = File(path)
        self.assertFileDoesNotExist(path)
        self.io.compress(self.file_members, archive)
        self.assertFileExists(path)
        self.assertTrue(archive.is_regular_file())
        compressed_archive_bytes = archive.read_all_bytes()
        magic_bytes = compressed_archive_bytes[:6]
        xz_tar_magic_bytes = bytes.fromhex("fd377a585a00")
        self.assertEqual(magic_bytes, xz_tar_magic_bytes)
        check_directory = File(self.create_directory("check"))
        self.io.extract(archive, check_directory)
        self.assert_directory_equals_expected_extracted(check_directory)

    @skipIfNotLzmaAvailable()
    def test_extract_tar_xz_archive_to_directory(self):
        archive = File(self.create_path("test-archive.tar.xz"))
        self.io.compress(self.file_members, archive)
        self.assertFileExists(archive.path)

        extract_directory = File(self.create_directory("extracted"))
        self.io.extract(archive, extract_directory)
        self.assertFileExists(archive.path)
        self.assertDirectoryExists(extract_directory.path)
        self.assert_directory_equals_expected_extracted(extract_directory)

    @skipIfNotLzmaAvailable()
    def test_read_packed_members_from_tar_xz_archive(self):
        archive = File(self.create_path("test-archive.tar.xz"))
        self.io.compress(self.file_members, archive)
        self.assertFileExists(archive.path)

        packed_members = self.io.read_packed_members(archive)
        self.assertEqual(len(packed_members), 9)
        expected_memberset = {member.name for member in self.file_members}
        actual_memberset = {member.name for member in packed_members}
        self.assertEqual(actual_memberset, expected_memberset)

    @skipIfNotLzmaAvailable()
    def test_extract_tar_xz_archive_rejects_path_traversal(self):
        archive_path = self.create_path("traversal.tar.xz")
        with tarfile.open(archive_path, "w:xz") as tar_file:
            info = tarfile.TarInfo(name="../escaped.txt")
            data = b"escaped content"
            info.size = len(data)
            tar_file.addfile(info, io.BytesIO(data))

        archive = File(archive_path)
        extract_dir = File(self.create_directory("extracted"))
        with self.assertRaises(ArchiveFileIOException) as raised:
            self.io.extract(archive, extract_dir)

        self.assertIn(
            "Archive member path would escape destination directory",
            str(raised.exception)
        )

    @skipIfNotLzmaAvailable()
    def test_extract_tar_xz_archive_rejects_absolute_path_in_member(self):
        archive_path = self.create_path("absolute-path.tar.xz")
        with tarfile.open(archive_path, "w:xz") as tar_file:
            info = tarfile.TarInfo(name="/etc/escaped.txt")
            data = b"escaped content"
            info.size = len(data)
            tar_file.addfile(info, io.BytesIO(data))

        archive = File(archive_path)
        extract_dir = File(self.create_directory("extracted"))
        with self.assertRaises(ArchiveFileIOException) as raised:
            self.io.extract(archive, extract_dir)

        self.assertIn(
            "Archive member path would escape destination directory",
            str(raised.exception)
        )

    @skipIfNotLzmaAvailable()
    def test_compress_empty_member_list_produces_valid_tar_xz_archive(self):
        path = self.create_path("empty.tar.xz")
        archive = File(path)
        self.io.compress([], archive)
        self.assertFileExists(path)
        self.assertTrue(archive.is_regular_file())
        packed_members = self.io.read_packed_members(archive)
        self.assertEqual(len(packed_members), 0)


if __name__ == "__main__":
    ArchiveFileIOTestCase.run_tests()
