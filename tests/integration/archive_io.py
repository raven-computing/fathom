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
"""Integration base test cases for archive file I/O implementations."""

from raven.fathom.base import File
from raven.fathom.base import ArchiveFileMember

from tests.integration import FileSystemIntegrationTestCase


class ArchiveFileIOTestCase(FileSystemIntegrationTestCase):
    """Integration test base case class for `ArchiveFileIO` interface
    implementations.
    """

    def setUp(self):
        super().setUp()
        self.file_members = []
        self.path_extracted = None
        self.prepare_archive_files()

    def prepare_archive_files(self):
        """Creates a prepared extracted archive file directory tree."""
        path_files = self.create_directory("files")
        self.create_directory("data")
        self.create_directory("files/A")
        self.create_file("files/A/file_A", data=b"AAA")
        self.create_file("files/A/file_B", data=b"BBBB")
        self.create_directory("files/B")
        self.create_directory("files/B/C")
        self.create_directory("files/B/E")
        self.create_file("files/B/C/d", data=b"DDD")
        empty_file = self.create_file("files/B/C/d_empty")
        f_a_c = File(self.create_path("data/f_a_c.bin"))
        f_a_c.write_all(b"CCCCC")
        dir_a = ArchiveFileMember("A")
        dir_b = ArchiveFileMember("B")
        a_a = ArchiveFileMember("A/file_A", content=b"AAA")
        a_b = ArchiveFileMember("A/file_B", content=bytearray(b"BBBB"))
        a_c = ArchiveFileMember("A/file_C", content=File(f_a_c))
        dir_b_c = ArchiveFileMember("B/C")
        dir_b_e = ArchiveFileMember("B/E")
        b_c_d = ArchiveFileMember("B/C/d", content=b"DDD")
        b_c_d_empty = ArchiveFileMember("B/C/d_empty", content=empty_file)
        self.file_members = [
            dir_a, dir_b, a_a, a_b, a_c, dir_b_c, dir_b_e, b_c_d, b_c_d_empty
        ]
        self.path_extracted = path_files

    def create_fileset(self, directory_path):
        """Creates a set of str file names which represents the content
        of the specified directory, as paths relative to that directory.
        """
        return {
            file.path.relative_to(directory_path).as_posix()
            for file in File(directory_path).list_all_files()
        }

    def assert_directory_equals_expected_extracted(self, directory: File):
        """Asserts that the given directory contains all the files equal to the
        directory denoted by the `path_extracted` directory.
        """
        File(self.create_path("data/f_a_c.bin")).move(
            self.create_path("files/A/file_C")  # Normalise
        )
        expected_fileset = self.create_fileset(self.path_extracted)
        actual_fileset = self.create_fileset(directory.path)
        self.assertDirectoryContent(directory, expected_fileset)

        self.assertEqual(len(actual_fileset), len(expected_fileset))
        self.assertEqual(actual_fileset, expected_fileset)

        assert self.path_extracted is not None
        for expected_item in expected_fileset:
            expected_file = File(self.path_extracted / expected_item)
            actual_file = directory / expected_item
            self.assertEqual(
                expected_file.get_type(),
                actual_file.get_type(),
                f"Type of expected file '{expected_file}' is not the same "
                f"as type of actual file '{actual_file}'"
            )
            if expected_file.is_regular_file():
                self.assertEqual(
                    expected_file.read_all_bytes(),
                    actual_file.read_all_bytes(),
                    f"Content of expected file '{expected_file}' differs "
                    f"from content of actual file '{actual_file}'"
                )
