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
"""Unit tests for the virtual filesystem implementation."""

import types
import platform
import datetime
import warnings

from pathlib import PurePath

from raven.fathom.base import File, TemporaryFile, FileSystem
from raven.fathom.base.testing._vfs import VirtualFileSystem
from raven.fathom.base import FileType, FileSize, FileSizeUnit, FileMode
from raven.fathom.base import FilePermission, FileAccess
from raven.fathom.base import (
    InvalidFileModeException, CannotOpenFileException, FilePermissionException,
    FileLockAcquisitionException, FileTextDecodeException,
    SymbolicLinkResolutionException, DirectoryListingException,
    FileTextEncodeException, FileCopyException, FileCreationException,
    TemporaryFileCreationException, FileNotFoundException,
    InvalidFileStateException
)

from raven.fathom.base import FILE_READ_ALL, FILE_POSITION_BEGIN
from raven.fathom.base import FILE_RESIZE_TO_CURRENT_POSITION

from tests.unit import TestCase

# pylint: disable=C2801,C0103


class VFSTestCase(TestCase):
    """Helper class for VFS tests."""

    def setUp(self):
        super().setUp()
        self.sys_win32 = platform.system() == "Windows"
        self.sep = "\\" if self.sys_win32 else "/"
        self.testdir = (
            PurePath("C:\\testing")
            if self.sys_win32
            else PurePath("/testing")
        )
        self.drive = "C:" if self.sys_win32 else ""
        self.nl = "\r\n" if self.sys_win32 else "\n"
        self.fs = File.get_file_system()
        assert isinstance(self.fs , VirtualFileSystem)
        self.fs.flush_system()
        self.fs.create_directories(self.testdir)

    def create_path(self, file) -> PurePath:
        """Creates a path object for the given test file."""
        file = PurePath(file)
        if not file.is_absolute():
            file = self.testdir / file

        return file

    def create_path_str(self, file) -> str:
        """Creates a path string for the given test file."""
        return self.create_path(file).as_posix()

    def create_file(self, file, data=None, encoding="UTF-8") -> PurePath:
        """Creates a test file with the given path."""
        path = self.create_path(file)
        File.get_file_system().touch_file(path)
        if data is not None:
            f = File(path)
            if isinstance(data, str):
                f.text_encoding = encoding

            f.write_all(data)

        return path

    def create_directory(self, file):
        """Creates an empty test directory with the given path."""
        path = self.create_path(file)
        File.get_file_system().create_directories(path)
        return path

    def assertFileExists(self, file):
        """Asserts that the given file in fact exists in the filesystem."""
        file = self.create_path(file)
        if not File.get_file_system().check_exists(file, check_symlink=True):
            raise AssertionError(
                f"Expected that file '{file}' exists"
            )

    def assertFileDoesNotExist(self, file):
        """Asserts that the given file in fact does not exist
        in the filesystem.
        """
        file = self.create_path(file)
        if File.get_file_system().check_exists(file, check_symlink=False):
            raise AssertionError(
                f"Expected that file '{file}' does not exist"
            )

    def assertFileContent(self, file, expected_data, encoding="UTF-8"):
        """Asserts that the given regular file contains the expected data.

        Args:
            file: The file to check, as a `Path` or `str`.
            expected_data: The data that the given file is expected to contain,
                as a `bytes` or `str` object.
            encoding (str): The encoding of the text data which will be used
                when reading the file in case `expected_data` is specified
                as a `str`.

        Raises:
            AssertionError: If the assertion does not hold true.
        """
        bin_mode = True
        if isinstance(expected_data, str):
            bin_mode = False

        with File(file).open() as f:
            f.text_encoding = encoding
            file_content = f.read() if bin_mode else f.read_text()
            if file_content != expected_data:
                if bin_mode:
                    assert isinstance(file_content, bytes)
                    assert isinstance(expected_data, bytes)
                    data_hint = "binary"
                    expected = (
                        f"'{expected_data.hex()}'"
                        if expected_data else "''"
                    )
                    actual = (
                        f"'{file_content.hex()}'"
                        if file_content else "''"
                    )
                else:
                    assert isinstance(file_content, str)
                    assert isinstance(expected_data, str)
                    data_hint = "text"
                    expected = f"'{expected_data}'" if expected_data else "''"
                    actual = f"'{file_content}'" if file_content else "''"

                raise AssertionError(
                    f"File content in file '{file}' does not match "
                    f"expected {data_hint} data:\n"
                    "Expected:\n"
                    f"{expected}\n"
                    "Actual:\n"
                    f"{actual}\n"
                )

    def assertDirectoryContent(self, file, expected_data):
        """Asserts that the given directory contains the expected files.

        Args:
            file: The directory to check, as a `Path` or `str`.
            expected_data (set): The `set` of `str` file names that the
                given directory is expected to contain.

        Raises:
            AssertionError: If the assertion does not hold true.
        """
        if not isinstance(expected_data, set):
            raise TypeError(
                "Argument 'expected_data' must be specified as a set "
                f"but found {type(expected_data)}"
            )

        if any(not isinstance(member, str) for member in expected_data):
            raise TypeError(
                "Argument 'expected_data' must be specified as "
                "a set of str file names"
            )

        file_str = str(file)
        actual_data = set()
        fs = File.get_file_system()
        for item in fs.list_files_of_directory(file, recursive=True):
            file_in_dir = str(item)[len(file_str)+1:]
            actual_data |= {str(file_in_dir)}

        if actual_data != expected_data:
            unexpected = actual_data.difference(expected_data)
            missing = expected_data.difference(actual_data)
            unexpected_msg = missing_msg = ""
            if unexpected:
                unexpected_msg = f"Unexpected files found:\n{unexpected}\n\n"

            if missing:
                missing_msg = f"Missing files:\n{missing}\n"

            raise AssertionError(
                f"Directory content in directory '{file}' does not match "
                "expected data:\n\n"
                f"{unexpected_msg}"
                f"{missing_msg}"
            )


class TestVirtualFileSystem(VFSTestCase):
    """Tests the `VirtualFileSystem` class through the `File` API."""

    def test_can_create_empty_regular_file_from_string_path(self):
        path = self.create_path_str("test-file-empty.1")
        file = File(path)
        self.assertFalse(file.exists())
        self.assertFalse(file.is_open())
        file.create()
        self.assertTrue(file.exists())
        self.assertTrue(File(path).exists())
        self.assertFalse(file.is_open())
        self.assertEqual(file.name, "test-file-empty.1")
        self.assertEqual(file.path.as_posix(), path)

    def test_can_create_empty_regular_file_from_path_obj(self):
        path = self.create_path("test-file-empty.1")
        file = File(path)
        self.assertFalse(file.exists())
        self.assertFalse(file.is_open())
        file.create()
        self.assertTrue(file.exists())
        self.assertTrue(File(path).exists())
        self.assertFalse(file.is_open())
        self.assertEqual(file.name, "test-file-empty.1")
        self.assertEqual(file.path, path)

    def test_can_create_regular_file_if_it_already_exists(self):
        path = self.create_file("test-file")
        file = File(path)
        file.create()
        self.assertTrue(File(path).exists())
        self.assertFalse(file.is_open())

    def test_creating_regular_file_with_path_to_existing_dir_raises_ex(self):
        path = self.create_path("test-node")
        File(path).create_directory()
        file = File(path)
        with self.assertRaises(FileCreationException) as raised:
            file.create()

        self.assertIn("Failed to create regular file", str(raised.exception))
        self.assertIn(
            "File already exists but is directory",
            str(raised.exception)
        )
        self.assertEqual(raised.exception.file_path, str(path))
        self.assertTrue(File(path).is_directory())
        self.assertFalse(file.is_open())

    def test_creating_regular_file_with_path_to_symlink_raises_ex(self):
        reg_file = self.create_file("test-file")
        path = self.create_path("test-node")
        File(path).create_symbolic_link(reg_file)
        file = File(path)
        with self.assertRaises(FileCreationException) as raised:
            file.create()

        self.assertIn("Failed to create regular file", str(raised.exception))
        self.assertIn(
            "File already exists but is symbolic link",
            str(raised.exception)
        )
        self.assertEqual(raised.exception.file_path, str(path))
        self.assertTrue(File(path).exists())
        self.assertFileExists(reg_file)

    def test_can_clone_file_object(self):
        file = File(self.create_path("test-file"))
        clone = File(file)
        self.assertIsNot(file, clone)
        self.assertEqual(file, clone)

    def test_can_create_empty_directory_from_string_path(self):
        path = self.create_path_str("test-dir-empty")
        file = File(path)
        self.assertFalse(file.exists())
        self.assertFalse(file.is_open())
        file.create_directory()
        self.assertTrue(file.exists())
        self.assertTrue(File(path).is_directory())
        self.assertDirectoryContent(path, set())
        self.assertFalse(file.is_open())
        self.assertEqual(file.name, "test-dir-empty")
        self.assertEqual(file.path.as_posix(), path)

    def test_can_create_empty_directory_from_path_obj(self):
        path = self.create_path("test-dir-empty")
        file = File(path)
        self.assertFalse(file.exists())
        self.assertFalse(file.is_open())
        file.create_directory()
        self.assertTrue(file.exists())
        self.assertTrue(File(path).is_directory())
        self.assertDirectoryContent(path, set())
        self.assertFalse(file.is_open())
        self.assertEqual(file.name, "test-dir-empty")
        self.assertEqual(file.path, path)

    def test_can_create_directory_if_it_already_exists(self):
        path = self.create_path("a-test-dir")
        file = File(path)
        self.assertFileDoesNotExist(path)
        file.create_directory()
        File(path / "a-test-file").create()
        file.create_directory()
        self.assertTrue(file.exists())
        self.assertTrue(file.is_directory())
        self.assertFalse(file.is_open())
        self.assertTrue(File(path).is_directory())
        self.assertDirectoryContent(path, {"a-test-file"})

    def test_creating_directory_where_nondir_file_already_exists_raises(self):
        path = self.create_file("a-test-file-where-a-dir-should-be-created")
        file = File(path)
        with self.assertRaises(FileCreationException) as raised:
            file.create_directory()

        self.assertIn("Failed to create directory", str(raised.exception))
        self.assertIn(
            "File already exists but is regular file",
            str(raised.exception)
        )
        self.assertEqual(raised.exception.file_path, str(path))
        self.assertTrue(file.exists())
        self.assertTrue(file.is_regular_file())
        self.assertFalse(file.is_open())
        self.assertFileExists("a-test-file-where-a-dir-should-be-created")

    def test_creating_directory_when_parent_does_not_exist_raises_ex(self):
        path = self.create_path("this-dir-does-not-exist/the-target-dir")
        file = File(path)
        with self.assertRaises(FileNotFoundException) as raised:
            file.create_directory()

        self.assertIn("Failed to create directory", str(raised.exception))
        self.assertIn(
            "because its parent does not exist",
            str(raised.exception)
        )
        self.assertEqual(raised.exception.file_path, str(path))
        self.assertFalse(file.exists())
        self.assertFalse(file.is_directory())
        self.assertFalse(file.is_open())
        self.assertFileDoesNotExist("this-dir-does-not-exist/the-target-dir")
        self.assertFileDoesNotExist("this-dir-does-not-exist")

    def test_creating_directory_when_parent_has_wrong_filetype_raises_ex(self):
        path = self.create_path("a_regular_file/the-target-dir")
        self.create_file(path.parent)
        file = File(path)
        with self.assertRaises(FileCreationException) as raised:
            file.create_directory()

        self.assertIn("Failed to create directory", str(raised.exception))
        self.assertIn(
            "Parent file already exists but is not a directory",
            str(raised.exception)
        )
        self.assertEqual(raised.exception.file_path, str(path))
        self.assertFalse(file.exists())
        self.assertFalse(file.is_directory())
        self.assertFalse(file.is_open())
        self.assertFileDoesNotExist(path)
        self.assertFileExists(path.parent)

    def test_can_create_directory_tree_from_string_path(self):
        path = self.create_path_str("parent-a/parent-b/target-dir")
        file = File(path)
        file.create_directory_tree()
        self.assertTrue(file.exists())
        self.assertTrue(file.is_directory())
        self.assertTrue(File(file.path.parent).is_directory())
        self.assertTrue(File(file.path.parent.parent).is_directory())
        self.assertDirectoryContent(path, set())
        self.assertFalse(file.is_open())
        self.assertEqual(file.name, "target-dir")

    def test_can_create_directory_tree_from_path_obj(self):
        path = self.create_path("parent-a/parent-b/target-dir")
        file = File(path)
        file.create_directory_tree()
        self.assertTrue(file.exists())
        self.assertTrue(File(path).is_directory())
        self.assertTrue(File(path.parent).is_directory())
        self.assertTrue(File(path.parent.parent).is_directory())
        self.assertDirectoryContent(path, set())
        self.assertFalse(file.is_open())
        self.assertEqual(file.name, "target-dir")

    def test_can_create_directory_tree_if_it_already_exists(self):
        path = self.create_path("parent-a/parent-b/target-dir")
        File(path.parent.parent).create_directory()
        self.assertFileExists(path.parent.parent)
        file = File(path)
        file.create_directory_tree()
        self.assertTrue(file.exists())
        self.assertTrue(File(path).is_directory())
        self.assertTrue(File(path.parent).is_directory())
        self.assertTrue(File(path.parent.parent).is_directory())
        self.assertDirectoryContent(path, set())
        self.assertFalse(file.is_open())
        self.assertEqual(file.name, "target-dir")

    def test_creating_directory_tree_where_file_already_exists_raises(self):
        path = self.create_path("parent-a/parent-b/target-dir")
        self.create_file(path.parent.parent)
        file = File(path)
        with self.assertRaises(FileCreationException) as raised:
            file.create_directory_tree()

        self.assertIn("Failed to create directory", str(raised.exception))
        self.assertIn(
            "File already exists but is not a directory",
            str(raised.exception)
        )
        self.assertEqual(raised.exception.file_path, str(path))
        self.assertFalse(file.exists())
        self.assertFileDoesNotExist(path)
        self.assertFileDoesNotExist(path.parent)
        self.assertFileExists(path.parent.parent)
        self.assertFalse(file.is_open())

    def test_creating_dir_tree_when_parent_cannot_be_created_raises_ex(self):
        path = self.create_path("parent-a/parent-b/target-dir")
        path_non_writable = path.parent.parent
        self.create_directory(path_non_writable)
        File(path_non_writable).set_permission(
            FilePermission.of(
                owner=FileAccess.of(readable=True),
                group=FileAccess.of(readable=True),
                other=FileAccess.of(readable=True)
            )
        )
        file = File(path)
        with self.assertRaises(FilePermissionException) as raised:
            file.create_directory_tree()

        self.assertIn("Failed to create directory", str(raised.exception))
        self.assertIn("or one of its parents", str(raised.exception))
        self.assertIn("Permission denied", str(raised.exception))
        self.assertIn(
            f"File '{path_non_writable}' of type directory is not writable: ",
            str(raised.exception)
        )
        self.assertEqual(raised.exception.file_path, str(path))
        self.assertFalse(file.exists())
        self.assertFileDoesNotExist(path)
        self.assertFileDoesNotExist(path.parent)
        self.assertFileExists(path_non_writable)
        self.assertFalse(file.is_open())

    def test_creating_dir_tree_when_parent_has_wrong_file_type_raises_ex(self):
        path = self.create_path("parent-a/parent-b/target-dir")
        self.create_directory(path.parent.parent)
        # Create parent as regular file, so that subdir cannot be created
        self.create_file(path.parent)
        file = File(path)
        with self.assertRaises(FileCreationException) as raised:
            file.create_directory_tree()

        self.assertIn("Failed to create directory", str(raised.exception))
        self.assertIn(
            "File already exists but is not a directory",
            str(raised.exception)
        )
        self.assertEqual(raised.exception.file_path, str(path))
        self.assertFalse(file.exists())
        self.assertFileDoesNotExist(path)
        self.assertFileExists(path.parent)
        self.assertFileExists(path.parent.parent)
        self.assertFalse(file.is_open())

    def test_can_create_symbolic_link_from_string_path(self):
        target_path = self.create_path_str("test-target-file")
        self.create_file(target_path)
        target_file = File(target_path)
        link_path = self.create_path_str("test-link-file")
        link_file = File(link_path)
        self.assertFalse(link_file.exists())
        self.assertFalse(link_file.is_open())
        link_file.create_symbolic_link(target_file)
        self.assertTrue(link_file.exists())
        self.assertFileExists(link_path)
        self.assertFileExists(target_path)
        self.assertFalse(link_file.is_open())
        self.assertFalse(target_file.is_open())
        self.assertEqual(link_file.name, "test-link-file")
        self.assertEqual(target_file.name, "test-target-file")
        self.assertEqual(link_file.path.as_posix(), link_path)
        self.assertEqual(target_file.path.as_posix(), target_path)

    def test_can_create_symbolic_link_from_path_obj(self):
        target_path = self.create_path("test-target-file")
        self.create_file(target_path)
        target_file = File(target_path)
        link_path = self.create_path("test-link-file")
        link_file = File(link_path)
        self.assertFalse(link_file.exists())
        self.assertFalse(link_file.is_open())
        link_file.create_symbolic_link(target_file)
        self.assertTrue(link_file.exists())
        self.assertFileExists(link_path)
        self.assertFileExists(target_path)
        self.assertFalse(link_file.is_open())
        self.assertFalse(target_file.is_open())
        self.assertEqual(link_file.name, "test-link-file")
        self.assertEqual(target_file.name, "test-target-file")
        self.assertEqual(link_file.path, link_path)
        self.assertEqual(target_file.path, target_path)

    def test_can_create_symbolic_link_for_regular_file(self):
        test_data = "TEST_DATA_FILE_CONTENT"
        path = self.create_path("test-regular-target-file")
        self.create_file(path, test_data)
        target_file = File(path)
        link_file = File(self.create_path("test-link-file"))
        link_file.create_symbolic_link(target_file)
        self.assertTrue(link_file.exists())
        self.assertFileExists(link_file.path)
        self.assertEqual(link_file.read_all_text(), test_data)
        self.assertFileContent(link_file.path, test_data)

    def test_can_create_symbolic_link_for_directory(self):
        test_data = "TEST_DATA_FILE_CONTENT"
        path = self.create_directory("dir_a/dir_b/dir_c")
        target_dir = File(path)
        path = self.create_file("dir_a/dir_b/dir_c/test-file", test_data)
        link_dir = File(self.create_path("test-link-dir"))
        link_dir.create_symbolic_link(target_dir)
        self.assertTrue(link_dir.exists())
        self.assertFileExists(link_dir.path)
        file = File(self.create_path("test-link-dir/test-file"))
        self.assertEqual(file.read_all_text(), test_data)
        self.assertFileContent(file.path, test_data)

    def test_can_create_symbolic_link_for_another_symbolic_link(self):
        test_data = "TEST_DATA_FILE_CONTENT"
        target_path = self.create_file("test-regular-target-file", test_data)
        target_file = File(target_path)
        link_a_file = File(self.create_path("test-link-a-file"))
        link_a_file.create_symbolic_link(target_file)
        link_b_file = File(self.create_path("test-link-b-file"))
        link_b_file.create_symbolic_link(link_a_file)
        self.assertTrue(link_b_file.exists())
        self.assertFileExists(link_b_file.path)
        self.assertEqual(link_b_file.read_all_text(), test_data)
        self.assertFileContent(link_b_file.path, test_data)

    def test_get_symbolic_link_target(self):
        path_file = self.create_file("regular-file")
        path_link_1 = self.create_path("link-1")
        path_link_2 = self.create_path("link-2")
        File(path_link_1).create_symbolic_link(File(path_file))
        File(path_link_2).create_symbolic_link(File(path_link_1))
        fs = File.get_file_system()
        self.assertEqual(fs.get_symbolic_link_target(path_file), path_file)
        self.assertIs(fs.get_symbolic_link_target(path_file), path_file)
        self.assertEqual(fs.get_symbolic_link_target(path_link_1), path_file)
        self.assertEqual(fs.get_symbolic_link_target(path_link_2), path_link_1)
        File(path_file).remove()  # Make broken symlink
        self.assertEqual(fs.get_symbolic_link_target(path_link_1), path_file)

    def test_get_absolute_symbolic_link_target(self):
        path_file = self.create_file("regular-file")
        path_link_1 = PurePath("link-1")
        path_link_2 = PurePath("link-2")
        File(path_link_1).create_symbolic_link(File(path_file))
        File(path_link_2).create_symbolic_link(File(path_link_1))
        fs = File.get_file_system()
        self.assertEqual(
            fs.get_symbolic_link_target(path_file, absolute=True), path_file
        )
        self.assertEqual(
            fs.get_symbolic_link_target(PurePath(path_link_1), absolute=True),
            path_file
        )
        self.assertEqual(
            fs.get_symbolic_link_target(PurePath(path_link_2), absolute=True),
            PurePath("/") / path_link_1
        )
        File(path_file).remove()  # Make broken symlink
        self.assertEqual(
            fs.get_symbolic_link_target(PurePath(path_link_1), absolute=True),
            path_file
        )

    def test_can_follow_multiple_symbolic_links(self):
        test_data = "TEST_DATA_FILE_CONTENT"
        target_path = self.create_file("test-regular-target-file", test_data)
        target_file = File(target_path)
        link_a_file = File(self.create_path("test-link-a-file"))
        link_a_file.create_symbolic_link(target_file)
        link_b_file = File(self.create_path("test-link-b-file"))
        link_b_file.create_symbolic_link(link_a_file)
        link_c_file = File(self.create_path("test-link-c-file"))
        link_c_file.create_symbolic_link(link_b_file)
        link_d_file = File(self.create_path("test-link-d-file"))
        link_d_file.create_symbolic_link(link_c_file)
        self.assertTrue(link_d_file.exists())
        self.assertFileExists(link_d_file.path)
        resolved_file = link_d_file.resolve_symbolic_links()
        self.assertEqual(resolved_file, target_file)
        self.assertEqual(resolved_file.read_all_text(), test_data)
        self.assertFileContent(resolved_file.path, test_data)

    def test_can_resolve_symbolic_links_anywhere_in_path(self):
        test_data = "TEST_DATA_FILE_CONTENT"
        base_dir = self.create_directory("a")
        self.create_file("a/test-file.txt", test_data)
        link = File(self.create_path("b"))
        link.create_symbolic_link(base_dir)
        file = File(self.create_path("b/test-file.txt"))
        self.assertTrue(file.exists())
        self.assertEqual(
            str(file.resolve_symbolic_links()),
            str(File(self.create_path("a/test-file.txt")))
        )
        self.assertEqual(file.read_all_text(), test_data)
        file.follow_symlinks = False
        self.assertEqual(
            file.resolve_symbolic_links(),
            File(self.create_path("a/test-file.txt"))
        )
        self.assertTrue(file.get_parent_directory().exists())
        self.assertTrue(file.exists())
        self.assertEqual(file.read_all_text(), test_data)

    def test_attempting_to_resolve_non_symlink_returns_same_file(self):
        path = self.create_file("test-regular-file")
        file = File(path)
        resolved_file = file.resolve_symbolic_links()
        self.assertIsInstance(resolved_file, File)
        self.assertEqual(resolved_file, file)

    def test_attempting_to_resolve_broken_symlink_raises_exception(self):
        target_path = self.create_file("test-regular-target-file")
        target_file = File(target_path)
        link_file = File(self.create_path("test-link-file"))
        link_file.create_symbolic_link(target_file)
        target_file.remove()
        with self.assertRaises(SymbolicLinkResolutionException) as raised:
            link_file.resolve_symbolic_links()

        self.assertIn("Failed to resolve symbolic link", str(raised.exception))
        self.assertIn("Cannot follow symbolic link", str(raised.exception))
        self.assertIn("Target does not exist", str(raised.exception))
        self.assertIn("broken link", str(raised.exception))
        self.assertEqual(raised.exception.file_path, str(link_file.path))

    def test_attempting_to_resolve_symlink_loop_raises_exception(self):
        test_data = "TEST_DATA_FILE_CONTENT"
        target_path = self.create_file("test-file", test_data)
        target_file = File(target_path)
        link_a_file = File(self.create_path("link-a"))
        link_a_file.create_symbolic_link(target_file)
        link_b_file = File(self.create_path("link-b"))
        link_b_file.create_symbolic_link(link_a_file)
        link_c_file = File(self.create_path("link-c"))
        link_c_file.create_symbolic_link(link_b_file)
        link_d_file = File(self.create_path("link-d"))
        link_d_file.create_symbolic_link(link_c_file)
        link_a_file.remove()
        link_a_file.create_symbolic_link(link_d_file)
        with self.assertRaises(SymbolicLinkResolutionException) as raised:
            link_d_file.resolve_symbolic_links()

        self.assertIn(
            "Failed to resolve symbolic links in path",
            str(raised.exception)
        )
        self.assertIn("Symlink loop detected", str(raised.exception))
        self.assertEqual(raised.exception.file_path, str(link_d_file.path))

    def test_can_resolve_symlink_for_root_path(self):
        self.assertEqual(
            str(File("/").resolve_symbolic_links()),
            str(File("/"))
        )

    def test_can_detect_broken_symlink_anywhere_in_path(self):
        test_data = "TEST_DATA_FILE_CONTENT"
        dir_a_b = self.create_directory("a/b")
        dir_a_c = self.create_path("a/c")
        dir_d = self.create_path("d")
        test_file = self.create_file("a/b/test-file.txt", test_data)
        File(dir_a_c).create_symbolic_link(File("b"))
        File(dir_d).create_symbolic_link(dir_a_c)
        file = File(self.create_path("d/test-file.txt"))
        self.assertTrue(file.exists())
        self.assertEqual(file.read_all_text(), test_data)
        resolved = File(test_file).resolve_symbolic_links()
        self.assertIsInstance(resolved, File)
        self.assertEqual(str(resolved), str(test_file))
        resolved = file.resolve_symbolic_links()
        self.assertIsInstance(resolved, File)
        self.assertEqual(str(resolved), str(test_file))
        resolved = File(dir_d).resolve_symbolic_links()
        self.assertEqual(str(resolved), str(self.create_path("a/b")))
        File(dir_a_b).remove()
        resolved = File(test_file).resolve_symbolic_links()
        self.assertEqual(str(resolved), str(test_file))
        with self.assertRaises(SymbolicLinkResolutionException) as raised:
            File(dir_d).resolve_symbolic_links()

        self.assertIn(
            f"Failed to resolve symbolic links in path '{dir_d}'.",
            str(raised.exception)
        )
        self.assertIn(
            f"Cannot follow symbolic link '{dir_a_c}'.",
            str(raised.exception)
        )
        self.assertIn(
            f"Target does not exist: '{dir_a_b}' (broken link)",
            str(raised.exception)
        )
        self.assertEqual(raised.exception.file_path, str(dir_d))
        File.get_file_system().remove(dir_a_c, follow_symlinks=False)
        with self.assertRaises(SymbolicLinkResolutionException) as raised:
            File(dir_d).resolve_symbolic_links()

        self.assertIn(
            f"Failed to resolve symbolic links in path '{dir_d}'.",
            str(raised.exception)
        )
        self.assertIn(
            f"Cannot follow symbolic link '{dir_d}'.",
            str(raised.exception)
        )
        self.assertIn(
            f"Target does not exist: '{dir_a_c}' (broken link)",
            str(raised.exception)
        )
        self.assertEqual(raised.exception.file_path, str(dir_d))

    def test_can_access_file_system_instance(self):
        fs_1 = File.get_file_system()
        fs_2 = File.get_file_system()
        self.assertIsInstance(fs_1, FileSystem)
        self.assertIsInstance(fs_2, FileSystem)
        self.assertIs(fs_1, fs_2)

    def test_can_get_and_set_default_text_encoding(self):
        original_default = "UTF-8"
        obtained_default = File.get_default_text_encoding()
        self.assertEqual(obtained_default, original_default)
        file = File(self.create_path("test-text-file.txt"))
        instance_text_encoding = file.text_encoding
        self.assertEqual(instance_text_encoding, original_default)
        changed_default = "UTF-16LE"
        File.set_default_text_encoding(changed_default)
        obtained_default = File.get_default_text_encoding()
        self.assertEqual(obtained_default, changed_default)
        file = File(self.create_path("test-text-file_2.txt"))
        instance_text_encoding = file.text_encoding
        self.assertEqual(instance_text_encoding, changed_default)
        File.set_default_text_encoding(original_default)
        obtained_default = File.get_default_text_encoding()
        self.assertEqual(obtained_default, original_default)

    def test_can_move_regular_file(self):
        test_data = "TEST_DATA_FILE_CONTENT"
        source_path = self.create_file("test-file-source", test_data)
        source_file = File(source_path)
        target_file = File(self.create_path("test-file-target"))
        self.assertTrue(source_file.exists())
        self.assertFileExists(source_file.path)
        self.assertFalse(target_file.exists())
        self.assertFileDoesNotExist(target_file.path)
        source_file.move(target_file)
        self.assertFalse(source_file.exists())
        self.assertFileDoesNotExist(source_file.path)
        self.assertTrue(target_file.exists())
        self.assertFileExists(target_file.path)
        self.assertEqual(target_file.read_all_text(), test_data)
        self.assertFileContent(target_file.path, test_data)

    def test_can_move_directory(self):
        test_data = "TEST_DATA_FILE_CONTENT"
        source_dir_1 = File(self.create_directory("dir_a"))
        source_dir_2 = File(self.create_directory("dir_a/dir_b"))
        test_data_file = File(
            self.create_file("dir_a/dir_b/test-data-file", test_data)
        )
        target_dir = File(self.create_path("dir-target"))
        self.assertTrue(source_dir_1.exists())
        self.assertFileExists(source_dir_1.path)
        self.assertTrue(source_dir_2.exists())
        self.assertFileExists(source_dir_2.path)
        self.assertFalse(target_dir.exists())
        self.assertFileDoesNotExist(target_dir.path)
        source_dir_1.move(target_dir)
        self.assertFalse(source_dir_1.exists())
        self.assertFileDoesNotExist(source_dir_1.path)
        self.assertTrue(target_dir.exists())
        self.assertFileExists(target_dir.path)
        self.assertFalse(test_data_file.exists())
        self.assertFileDoesNotExist(test_data_file.path)
        moved_test_data_file = File(
            self.create_path("dir-target/dir_b/test-data-file")
        )
        self.assertTrue(moved_test_data_file.exists())
        self.assertFileExists(moved_test_data_file.path)
        self.assertEqual(moved_test_data_file.read_all_text(), test_data)
        self.assertFileContent(moved_test_data_file.path, test_data)

    def test_can_move_symbolic_link(self):
        test_data = "TEST_DATA_FILE_CONTENT"
        data_file = File(self.create_file("test-data-file", test_data))
        link_source = File(self.create_path("A-test-link-11"))
        link_source.create_symbolic_link(data_file)
        self.assertTrue(link_source.exists())
        link_target = File(self.create_path("B-test-link-22"))
        link_source.follow_symlinks = False
        link_source.move(link_target)
        self.assertFalse(link_source.exists())
        self.assertFileDoesNotExist(link_source.path)
        self.assertTrue(link_target.exists())
        self.assertFileExists(link_target.path)
        self.assertEqual(link_target.read_all_text(), test_data)
        self.assertFileContent(link_target.path, test_data)
        self.assertEqual(link_target.resolve_symbolic_links(), data_file)

    def test_can_move_target_of_symbolic_link(self):
        test_data = "TEST_DATA_FILE_CONTENT"
        file = File(self.create_file("test-file", test_data))
        link_file = File(self.create_path("test-link"))
        link_file.create_symbolic_link(file)
        target_file = File(self.create_path("moved-target-file"))
        link_file.follow_symlinks = True
        link_file.move(target_file)
        self.assertFalse(file.exists())
        self.assertFileDoesNotExist(file.path)
        self.assertFalse(link_file.exists())
        self.assertFileDoesNotExist(link_file.path)
        self.assertTrue(target_file.exists())
        self.assertFileExists(target_file.path)
        self.assertEqual(target_file.read_all_text(), test_data)
        self.assertFileContent(target_file.path, test_data)
        self.assertEqual(target_file.get_type(), FileType.REGULAR_FILE)

    def test_can_move_file_when_target_file_already_exists(self):
        test_data_source = "TEST_SOURCE_FILE_CONTENT"
        test_data_target = "TEST_TARGET_FILE_CONTENT"
        source_path = self.create_file("test-file-source", test_data_source)
        source_file = File(source_path)
        target_path = self.create_file("test-file-target", test_data_target)
        target_file = File(target_path)
        self.assertFileExists(source_file.path)
        self.assertFileExists(target_file.path)
        source_file.move(target_file)
        self.assertFalse(source_file.exists())
        self.assertFileDoesNotExist(source_file.path)
        self.assertTrue(target_file.exists())
        self.assertFileExists(target_file.path)
        self.assertEqual(target_file.read_all_text(), test_data_source)
        self.assertFileContent(target_file.path, test_data_source)

    def test_can_move_directory_when_target_directory_already_exists(self):
        test_data = "TEST_DATA_FILE_CONTENT"
        source_dir_1 = File(self.create_directory("dir_a"))
        source_dir_2 = File(self.create_directory("dir_a/dir_b"))
        test_data_file = File(
            self.create_file("dir_a/dir_b/test-data-file", test_data)
        )
        target_path = self.create_directory("dir-target")
        target_dir = File(target_path)
        self.assertFileExists(source_dir_1.path)
        self.assertFileExists(source_dir_2.path)
        self.assertFileExists(target_dir.path)
        source_dir_1.move(target_dir)
        self.assertFalse(source_dir_1.exists())
        self.assertFileDoesNotExist(source_dir_1.path)
        self.assertTrue(target_dir.exists())
        self.assertFileExists(target_dir.path)
        self.assertFalse(test_data_file.exists())
        self.assertFileDoesNotExist(test_data_file.path)
        moved_test_data_file = File(
            self.create_path("dir-target/dir_b/test-data-file")
        )
        self.assertTrue(moved_test_data_file.exists())
        self.assertFileExists(moved_test_data_file.path)
        self.assertEqual(moved_test_data_file.read_all_text(), test_data)
        self.assertFileContent(moved_test_data_file.path, test_data)

    def test_attempting_to_move_open_file_raises_exception(self):
        test_data = "TEST_DATA_FILE_CONTENT"
        source_path = self.create_file("test-file-source", test_data)
        source_file = File(source_path)
        target_file = File(self.create_path("test-file-target"))
        with source_file.open(FileMode.READ_WRITE):
            with self.assertRaises(InvalidFileStateException) as raised:
                source_file.move(target_file)

        self.assertIn("Cannot move file", str(raised.exception))
        self.assertIn(
            "File is open and must first be closed before it can be moved",
            str(raised.exception)
        )
        self.assertEqual(
            raised.exception.file_path,
            str(source_file.path)
        )
        self.assertFileExists(source_file.path)
        self.assertFileDoesNotExist(target_file.path)
        self.assertFileContent(source_file.path, test_data)

    def test_attempting_to_move_nonexistent_file_raises_exception(self):
        file = File(self.create_path("nonexistent-file"))
        with self.assertRaises(FileNotFoundException) as raised:
            file.move("target")

        self.assertIn("Failed to move file ", str(raised.exception))
        self.assertIn("to destination at ", str(raised.exception))
        self.assertIn("File does not exist", str(raised.exception))
        self.assertEqual(raised.exception.file_path, str(file.path))

    def test_can_copy_regular_file(self):
        test_data = "TEST_DATA_FILE_CONTENT"
        source_path = self.create_file("test-file-source", test_data)
        source_file = File(source_path)
        target_file = File(self.create_path("test-file-target"))
        self.assertFileExists(source_path)
        self.assertFileDoesNotExist(target_file.path)
        source_file.copy(target_file)
        self.assertTrue(source_file.exists())
        self.assertFileExists(source_file.path)
        self.assertTrue(target_file.exists())
        self.assertFileExists(target_file.path)
        self.assertFileContent(source_path, test_data)
        self.assertFileContent(target_file.path, test_data)

    def test_can_copy_directory(self):
        test_data = "TEST_DATA_FILE_CONTENT"
        source_dir_1 = File(self.create_directory("dir_a"))
        source_dir_2 = File(self.create_directory("dir_a/dir_b"))
        test_data_file = File(
            self.create_file("dir_a/dir_b/test-data-file", test_data)
        )
        target_dir = File(self.create_path("dir-target"))
        self.assertFileDoesNotExist(target_dir.path)
        source_dir_1.copy(target_dir)
        self.assertTrue(File(source_dir_1.path).is_directory())
        self.assertTrue(File(source_dir_2.path).is_directory())
        self.assertFileExists(test_data_file.path)
        self.assertTrue(File(target_dir.path).is_directory())
        self.assertTrue(File(target_dir.path / "dir_b").is_directory())
        copied_test_data_file = File(
            self.create_path("dir-target/dir_b/test-data-file")
        )
        self.assertFileExists(copied_test_data_file.path)
        self.assertFileContent(copied_test_data_file.path, test_data)
        self.assertFileContent(test_data_file.path, test_data)
        self.assertDirectoryContent(
            source_dir_1.path,
            {"dir_b", f"dir_b{self.sep}test-data-file"}
        )
        self.assertDirectoryContent(
            target_dir.path,
            {"dir_b", f"dir_b{self.sep}test-data-file"}
        )

    def test_can_copy_directory_which_already_exists_at_destination(self):
        test_data = "TEST_DATA_FILE_CONTENT"
        source_dir_1 = File(self.create_directory("dir_a"))
        source_dir_2 = File(self.create_directory("dir_a/dir_b"))
        test_data_file = File(
            self.create_file("dir_a/dir_b/test-data-file", test_data)
        )
        target_dir = File(self.create_directory("dir-target"))
        target_dir_2 = File(self.create_directory("dir-target/dir_b"))
        target_file_2 = File(
            self.create_file(
                "dir-target/dir_b/existent-data-file",
                "EXISTENT_CONTENT"
            )
        )
        self.assertTrue(File(target_dir.path).is_directory())
        source_dir_1.copy(target_dir)
        self.assertTrue(File(source_dir_1.path).is_directory())
        self.assertTrue(File(source_dir_2.path).is_directory())
        self.assertFileExists(test_data_file.path)
        self.assertTrue(File(target_dir.path).is_directory())
        self.assertTrue(File(target_dir_2.path).is_directory())
        self.assertFileExists(target_file_2.path)
        self.assertFileContent(target_file_2.path, "EXISTENT_CONTENT")
        copied_test_data_file = File(
            self.create_path("dir-target/dir_b/test-data-file")
        )
        self.assertFileExists(copied_test_data_file.path)
        self.assertFileContent(copied_test_data_file.path, test_data)
        self.assertFileContent(test_data_file.path, test_data)
        self.assertDirectoryContent(
            source_dir_1.path,
            {"dir_b", f"dir_b{self.sep}test-data-file"}
        )
        self.assertDirectoryContent(
            target_dir.path,
            {"dir_b",
             f"dir_b{self.sep}existent-data-file",
             f"dir_b{self.sep}test-data-file"}
        )

    def test_copying_dir_containing_symlink_copies_the_symlink_target(self):
        test_data = "TEST_DATA_FILE_CONTENT"
        source_dir_1 = File(self.create_directory("dir_a"))
        source_dir_2 = File(self.create_directory("dir_a/dir_b"))
        test_data_file = File(
            self.create_file("dir_a/dir_b/test-data-file", test_data)
        )
        test_link = File(self.create_path("dir_a/dir_b/test-link"))
        test_link.create_symbolic_link(test_data_file)
        target_dir = File(self.create_path("dir-target"))
        self.assertFileDoesNotExist(target_dir.path)
        source_dir_1.copy(target_dir)
        self.assertTrue(File(source_dir_1.path).is_directory())
        self.assertTrue(File(source_dir_2.path).is_directory())
        self.assertFileExists(test_data_file.path)
        self.assertTrue(File(target_dir.path).is_directory())
        self.assertTrue(File(target_dir.path / "dir_b").is_directory())
        self.assertFileExists(target_dir.path / "dir_b/test-data-file")
        target_link_file = File(target_dir.path / "dir_b/test-link")
        self.assertFileExists(target_link_file.path)
        self.assertFileContent(
            target_dir.path / "dir_b/test-data-file",
            test_data
        )
        self.assertFileContent(
            target_dir.path / "dir_b/test-link",
            test_data
        )
        self.assertTrue(test_link.is_symbolic_link())
        self.assertTrue(target_link_file.is_regular_file())
        self.assertFileContent(test_data_file.path, test_data)
        self.assertDirectoryContent(
            source_dir_1.path,
            {"dir_b", f"dir_b{self.sep}test-data-file",
             f"dir_b{self.sep}test-link"}
        )
        self.assertDirectoryContent(
            target_dir.path,
            {"dir_b",
             f"dir_b{self.sep}test-data-file",
             f"dir_b{self.sep}test-link"}
        )

    def test_copying_dir_containing_broken_symlink_raises_exception(self):
        test_data = "TEST_DATA_FILE_CONTENT"
        source_dir_with_broken_symlink = File(self.create_directory("dir_a"))
        self.create_directory("dir_a/dir_b")
        test_data_file = File(
            self.create_file("dir_a/dir_b/test-data-file", test_data)
        )
        test_link = File(self.create_path("dir_a/dir_b/test-broken-link"))
        test_link.create_symbolic_link(test_data_file)
        test_data_file.remove()
        target_dir = File(self.create_path("dir-target"))
        with self.assertRaises(FileCopyException) as raised:
            source_dir_with_broken_symlink.copy(target_dir)

        self.assertIn("Failed to copy", str(raised.exception))
        self.assertIn("to destination at", str(raised.exception))
        self.assertIn(
            "Failed to resolve symbolic links in path",
            str(raised.exception)
        )
        self.assertIn("Cannot follow symbolic link", str(raised.exception))
        self.assertIn("Target does not exist", str(raised.exception))
        self.assertIn("broken link", str(raised.exception))
        self.assertEqual(
            raised.exception.file_path,
            str(source_dir_with_broken_symlink.path))

    def test_attempting_to_copy_symbolic_link_raises_exception(self):
        test_data = "TEST_DATA_FILE_CONTENT"
        data_file = File(self.create_file("test-data-file", test_data))
        link_source = File(self.create_path("test-link"))
        link_source.create_symbolic_link(data_file)
        target = File(self.create_path("test-file-target"))
        link_source.follow_symlinks = False
        with self.assertRaises(FileCopyException) as raised:
            link_source.copy(target)

        self.assertIn("Cannot copy file", str(raised.exception))
        self.assertIn(
            "Only regular files and directories can be copied",
            str(raised.exception)
        )
        self.assertEqual(raised.exception.file_path, str(link_source))
        self.assertFileExists(link_source.path)
        self.assertFileExists(data_file.path)

    def test_attempting_to_copy_files_of_different_types_raises_ex(self):
        path_file = self.create_file("test-file")
        path_dir = self.create_directory("test-dir")
        file_file = File(path_file)
        file_dir = File(path_dir)
        with self.assertRaises(FileCopyException) as raised:
            file_file.copy(file_dir)

        self.assertIn("Cannot copy file", str(raised.exception))
        self.assertIn(
            "File at destination already exists but is of type DIRECTORY",
            str(raised.exception)
        )
        self.assertEqual(raised.exception.file_path, str(file_file.path))

        with self.assertRaises(FileCopyException) as raised:
            file_dir.copy(file_file)

        self.assertIn("Cannot copy file", str(raised.exception))
        self.assertIn(
            "File at destination already exists but is of type REGULAR_FILE",
            str(raised.exception)
        )
        self.assertEqual(raised.exception.file_path, str(file_dir.path))

    def test_attempting_to_copy_nonexistent_file_raises_exception(self):
        source_path = self.create_path("this-file-does-not-exist")
        nonexistent_file = File(source_path)
        target_file = self.create_path("test-file-target")
        with self.assertRaises(FileNotFoundException) as raised:
            nonexistent_file.copy(target_file)

        self.assertIn("Failed to copy file", str(raised.exception))
        self.assertIn("to destination at", str(raised.exception))
        self.assertEqual(
            raised.exception.file_path,
            str(nonexistent_file.path)
        )
        self.assertFileDoesNotExist(source_path)
        self.assertFileDoesNotExist(target_file)

    def test_attempting_to_copy_open_file_raises_exception(self):
        test_data = "TEST_DATA_FILE_CONTENT"
        source_path = self.create_file("test-file-source", test_data)
        source_file = File(source_path)
        target_file = File(self.create_path("test-file-target"))
        with source_file.open(FileMode.READ_WRITE):
            with self.assertRaises(InvalidFileStateException) as raised:
                source_file.copy(target_file)

        self.assertIn("Cannot copy file", str(raised.exception))
        self.assertIn(
            "File is open and must first be closed before it can be copied",
            str(raised.exception)
        )
        self.assertEqual(
            raised.exception.file_path,
            str(source_file.path)
        )
        self.assertFileExists(source_file.path)
        self.assertFileDoesNotExist(target_file.path)
        self.assertFileContent(source_file.path, test_data)

    def test_can_remove_regular_file(self):
        test_data = "TEST_DATA_FILE_CONTENT"
        file = File(self.create_file("test-file", test_data))
        self.assertTrue(file.exists())
        self.assertFileExists(file.path)
        file.remove()
        self.assertFalse(file.exists())
        self.assertFileDoesNotExist(file.path)

    def test_can_remove_directory(self):
        test_data = "TEST_DATA_FILE_CONTENT"
        test_dir = File(self.create_directory("dir_a/dir_b/dir_c"))
        test_file_1 = File(
            self.create_file("dir_a/dir_b/test-file", test_data)
        )
        test_file_2 = File(
            self.create_file("dir_a/dir_b/dir_c/test-file", test_data)
        )
        test_dir.remove()
        self.assertFalse(test_dir.exists())
        self.assertTrue(test_file_1.exists())
        self.assertFalse(test_file_2.exists())
        self.assertFileDoesNotExist(test_dir.path)
        self.assertFileExists(test_file_1.path)
        self.assertFileDoesNotExist(test_file_2.path)

    def test_can_remove_non_empty_directory(self):
        test_data = "TEST_DATA_FILE_CONTENT"
        self.create_directory("dir_a/dir_b/dir_c")
        self.create_file("dir_a/dir_b/test-file", test_data)
        self.create_file("dir_a/dir_b/dir_c/test-file", test_data)
        test_dir = File(self.create_path("dir_a"))
        test_dir.remove()
        self.assertFalse(test_dir.exists())
        self.assertFileDoesNotExist(test_dir.path)

    def test_can_remove_symbolic_link(self):
        test_data = "TEST_DATA_FILE_CONTENT"
        file = File(self.create_file("test-file", test_data))
        self.assertTrue(file.exists())
        self.assertFileExists(file.path)
        link = File(self.create_path("test-link"))
        link.create_symbolic_link(file)
        self.assertTrue(link.exists())
        self.assertFileExists(link.path)
        link.follow_symlinks = False
        link.remove()
        self.assertFalse(link.exists())
        self.assertFileDoesNotExist(link.path)
        self.assertTrue(file.exists())
        self.assertFileExists(file.path)

    def test_can_remove_target_of_symbolic_link(self):
        test_data = "TEST_DATA_FILE_CONTENT"
        file = File(self.create_file("test-file", test_data))
        link = File(self.create_path("test-link"))
        link.create_symbolic_link(file)
        link.follow_symlinks = True
        link.remove()
        self.assertFalse(file.exists())
        self.assertFileDoesNotExist(file.path)
        link.follow_symlinks = False
        self.assertFalse(link.exists())
        self.assertFileDoesNotExist(link.path)

    def test_attempting_to_remove_nonexistent_file_raises_exception(self):
        file = File(self.create_path("test-file-that-does-not-exist"))
        with self.assertRaises(FileNotFoundException) as raised:
            file.remove()

        self.assertIn("Failed to remove file ", str(raised.exception))
        self.assertIn("File does not exist", str(raised.exception))
        self.assertEqual(raised.exception.file_path, str(file.path))
        self.assertFalse(file.exists())

    def test_attempting_to_remove_open_file_raises_exception(self):
        test_data = "TEST_DATA_FILE_CONTENT"
        path = self.create_file("test-file", test_data)
        file = File(path)
        with file.open(FileMode.READ_WRITE):
            with self.assertRaises(InvalidFileStateException) as raised:
                file.remove()

        self.assertIn("Cannot remove file", str(raised.exception))
        self.assertIn(
            "File is open and must first be closed before it can be removed",
            str(raised.exception)
        )
        self.assertEqual(
            raised.exception.file_path,
            str(file.path)
        )
        self.assertFileExists(file.path)
        self.assertFileContent(file.path, test_data)

    def test_can_get_size_of_regular_file(self):
        test_data = "TEST_DATA_FILE_CONTENT"
        file = File(self.create_file("test-file"))
        size = file.size()
        self.assertIsInstance(size, FileSize)
        self.assertEqual(size.value, 0)
        self.assertEqual(size.unit, FileSizeUnit.BYTE)
        file.write_all(test_data)
        size = file.size()
        self.assertIsInstance(size, FileSize)
        self.assertEqual(size.value, len(test_data))
        self.assertEqual(size.unit, FileSizeUnit.BYTE)

    def test_can_get_size_of_directory(self):
        test_data = "TEST_DATA_FILE_CONTENT"
        test_dir = File(self.create_directory("dir_a/dir_b/dir_c"))
        self.create_file("dir_a/dir_b/dir_c/test-file", test_data)
        self.create_file("dir_a/dir_b/test-file-1", test_data)
        self.create_file("dir_a/dir_b/test-file-2", test_data)
        self.create_file("dir_a/test-file", test_data + "AAAA")
        # Get top-level directory
        test_dir = File(self.create_path("dir_a"))
        size = test_dir.size()
        self.assertIsInstance(size, FileSize)
        expected_size = (len(test_data) * 4) + 4
        self.assertEqual(size.value, expected_size)
        self.assertEqual(size.unit, FileSizeUnit.BYTE)

    def test_can_get_size_of_regular_file_via_symlink(self):
        test_data = "TEST_DATA_FILE_CONTENT"
        file = File(self.create_file("test-file"))
        link_file = File(self.create_path("test-link"))
        link_file.create_symbolic_link(file)
        size = link_file.size()
        self.assertIsInstance(size, FileSize)
        self.assertEqual(size.value, 0)
        self.assertEqual(size.unit, FileSizeUnit.BYTE)
        file.write_all(test_data)
        size = link_file.size()
        self.assertIsInstance(size, FileSize)
        self.assertEqual(size.value, len(test_data))
        self.assertEqual(size.unit, FileSizeUnit.BYTE)

    def test_getting_size_of_broken_symlink_raises_ex(self):
        file = File(self.create_file("test-file"))
        link_file = File(self.create_path("test-link"))
        link_file.create_symbolic_link(file)
        file.remove()
        with self.assertRaises(SymbolicLinkResolutionException) as raised:
            link_file.size()

        self.assertIn("Failed to resolve symbolic link", str(raised.exception))
        self.assertIn("Target does not exist", str(raised.exception))
        self.assertIn("broken link", str(raised.exception))
        self.assertEqual(raised.exception.file_path, str(link_file.path))

    def test_size_of_empty_directory_is_zero(self):
        test_dir = File(self.create_directory("dir_a/dir_b/dir_c"))
        self.create_directory("dir_a/dir_other")
        size = test_dir.size()
        self.assertIsInstance(size, FileSize)
        self.assertEqual(size.value, 0)
        self.assertEqual(size.unit, FileSizeUnit.BYTE)

    def test_getting_size_of_nonexistent_file_raises_exception(self):
        file = File(self.create_path("nonexistent-file"))
        with self.assertRaises(FileNotFoundException) as raised:
            file.size()

        self.assertIn("Failed to query size of file", str(raised.exception))
        self.assertIn("File does not exist", str(raised.exception))
        self.assertEqual(raised.exception.file_path, str(file.path))

    def test_checking_is_empty_for_empty_regular_file_returns_true(self):
        file = File(self.create_file("test-file"))
        self.assertIsInstance(file.is_empty(), bool)
        self.assertTrue(file.is_empty())

    def test_checking_is_empty_for_nonempty_regular_file_returns_false(self):
        file = File(self.create_file("test-file", data=b"A"))
        self.assertIsInstance(file.is_empty(), bool)
        self.assertFalse(file.is_empty())

    def test_checking_is_empty_for_empty_directory_returns_true(self):
        directory = File(self.create_directory("test-dir"))
        self.assertIsInstance(directory.is_empty(), bool)
        self.assertTrue(directory.is_empty())

    def test_checking_is_empty_for_nonempty_directory_returns_false(self):
        path = self.create_directory("test-dir")
        self.create_file("test-dir/a", data=b"A")
        directory = File(path)
        self.assertIsInstance(directory.is_empty(), bool)
        self.assertFalse(directory.is_empty())

    def test_checking_is_empty_for_dir_with_empty_file_returns_false(self):
        path = self.create_directory("test-dir")
        self.create_file("test-dir/a")
        directory = File(path)
        self.assertIsInstance(directory.is_empty(), bool)
        self.assertFalse(directory.is_empty())

    def test_checking_is_empty_for_symlink_to_empty_file_returns_true(self):
        target = self.create_file("test-file")
        file = File(self.create_path("test-link"))
        file.create_symbolic_link(target)
        self.assertTrue(file.is_symbolic_link())
        self.assertIsInstance(file.is_empty(), bool)
        self.assertTrue(file.is_empty())

    def test_check_is_empty_for_symlink_to_nonempty_file_returns_false(self):
        target = self.create_file("test-file", data=b"A")
        file = File(self.create_path("test-link"))
        file.create_symbolic_link(target)
        self.assertTrue(file.is_symbolic_link())
        self.assertIsInstance(file.is_empty(), bool)
        self.assertFalse(file.is_empty())

    def test_checking_is_empty_for_nonexistent_file_raises_exception(self):
        file = File(self.create_path("this-file-does-not-exist"))
        with self.assertRaises(FileNotFoundException) as raised:
            file.is_empty()

        self.assertIn("Failed to query size of file", str(raised.exception))
        self.assertIn("File does not exist", str(raised.exception))
        self.assertEqual(raised.exception.file_path, str(file.path))

    def test_can_determine_type_of_regular_file(self):
        file = File(self.create_file("test-file"))
        file_type = file.get_type()
        self.assertIsInstance(file_type, FileType)
        self.assertEqual(file_type, FileType.REGULAR_FILE)
        self.assertTrue(file.is_regular_file())

    def test_can_determine_type_of_directory(self):
        file = File(self.create_directory("test-dir"))
        file_type = file.get_type()
        self.assertIsInstance(file_type, FileType)
        self.assertEqual(file_type, FileType.DIRECTORY)
        self.assertTrue(file.is_directory())

    def test_can_determine_type_of_symbolic_link(self):
        path_file = self.create_file("test-target-file")
        path_link = self.create_path("test-link")
        file = File(path_link)
        file.create_symbolic_link(path_file)
        file.follow_symlinks = False
        file_type = file.get_type()
        self.assertIsInstance(file_type, FileType)
        self.assertEqual(file_type, FileType.SYMBOLIC_LINK)
        self.assertTrue(file.is_symbolic_link())

    def test_can_determine_type_of_symbolic_link_target(self):
        path_file = self.create_file("test-target-file")
        file = File(self.create_path("test-link"))
        file.create_symbolic_link(path_file)
        file_type = file.get_type()
        self.assertIsInstance(file_type, FileType)
        self.assertEqual(file_type, FileType.REGULAR_FILE)
        self.assertTrue(file.is_symbolic_link())

    def test_determining_type_of_nonexistent_file_raises_exception(self):
        path = self.create_path("this-file-does-not-exist")
        file = File(path)
        with self.assertRaises(FileNotFoundException) as raised:
            file.get_type()

        self.assertIn("Failed to obtain type of file", str(raised.exception))
        self.assertIn("No such file or directory", str(raised.exception))
        self.assertEqual(raised.exception.file_path, str(path))

    def test_determining_type_of_broken_symlink_raises_exception(self):
        path = self.create_file("test-file")
        file = File(path)
        link_file = File(self.create_path("test-link"))
        link_file.create_symbolic_link(file)
        file.remove()
        with self.assertRaises(SymbolicLinkResolutionException) as raised:
            link_file.get_type()

        self.assertIn("Failed to resolve symbolic link", str(raised.exception))
        self.assertIn("Target does not exist", str(raised.exception))
        self.assertIn("broken link", str(raised.exception))
        self.assertEqual(raised.exception.file_path, str(link_file.path))

    def test_is_regular_file_queries(self):
        file = File(self.create_file("test-file"))
        self.assertTrue(file.is_regular_file())
        self.assertFalse(file.is_directory())
        self.assertFalse(file.is_symbolic_link())
        self.assertFalse(file.is_socket())
        self.assertFalse(file.is_named_pipe())
        self.assertFalse(file.is_character_device())
        self.assertFalse(file.is_block_device())

    def test_is_directory_queries(self):
        file = File(self.create_directory("test-dir"))
        self.assertTrue(file.is_directory())
        self.assertFalse(file.is_regular_file())
        self.assertFalse(file.is_symbolic_link())
        self.assertFalse(file.is_socket())
        self.assertFalse(file.is_named_pipe())
        self.assertFalse(file.is_character_device())
        self.assertFalse(file.is_block_device())

    def test_is_symbolic_link_queries(self):
        path_file =self.create_file("test-target-file")
        file = File(self.create_path("test-link"))
        file.create_symbolic_link(path_file)
        self.assertTrue(file.is_symbolic_link())
        self.assertTrue(
            file.is_regular_file(),
            "is_regular_file() should follow symbolic links to their target"
        )
        self.assertFalse(file.is_directory())
        self.assertFalse(file.is_socket())
        self.assertFalse(file.is_named_pipe())
        self.assertFalse(file.is_character_device())
        self.assertFalse(file.is_block_device())

    def test_is_file_type_queries_for_nonexistent_file(self):
        file = File(self.create_path("nonexistent-file"))
        self.assertFalse(file.is_regular_file())
        self.assertFalse(file.is_directory())
        self.assertFalse(file.is_symbolic_link())
        self.assertFalse(file.is_socket())
        self.assertFalse(file.is_named_pipe())
        self.assertFalse(file.is_character_device())
        self.assertFalse(file.is_block_device())

    def test_can_get_parent_directory_from_regular_file(self):
        file = File(self.create_file("test-file"))
        self.assertEqual(file.get_parent_directory().path, self.testdir)

    def test_can_get_parent_directory_from_other_directory(self):
        file = File(self.create_directory("dir_a/dir_b/dir_c"))
        parent_1 = self.testdir / "dir_a/dir_b"
        path_parent_1 = file.get_parent_directory().path
        parent_2 = self.testdir / "dir_a"
        path_parent_2 = File(path_parent_1).get_parent_directory().path
        path_parent_3 = File(path_parent_2).get_parent_directory().path
        self.assertEqual(path_parent_1, parent_1)
        self.assertEqual(path_parent_2, parent_2)
        self.assertEqual(path_parent_3, self.testdir)

    def test_can_open_and_close_file(self):
        file = File(self.create_file("test-file"))
        self.assertFalse(file.is_open())
        instance_returned_by_open = file.open()
        self.assertIs(file, instance_returned_by_open)
        self.assertTrue(file.is_open())
        file.close()
        self.assertFalse(file.is_open())

    def test_can_open_and_close_file_with_all_supported_modes(self):
        path = self.create_path("test-file")
        for file_mode in FileMode:
            if not file_mode.can_create():
                self.create_file(path)

            file = File(path)
            self.assertFalse(file.is_open())
            file.open(file_mode)
            self.assertTrue(file.is_open())
            file.close()
            self.assertFalse(file.is_open())
            File(path).remove()

    def test_attempting_to_open_broken_symlink_raises_exception(self):
        target_path = self.create_file("test-file")
        target_file = File(target_path)
        link_file = File(self.create_path("test-link"))
        link_file.create_symbolic_link(target_file)
        target_file.remove()
        with self.assertRaises(SymbolicLinkResolutionException) as raised:
            link_file.open()

        self.assertIn("Failed to resolve symbolic link", str(raised.exception))
        self.assertIn("Target does not exist", str(raised.exception))
        self.assertIn("broken link", str(raised.exception))
        self.assertEqual(raised.exception.file_path, str(link_file.path))

    def test_file_mode_create(self):
        path = self.create_path("test-file")
        file = File(path)
        file.open(FileMode.CREATE).close()
        self.assertTrue(File(path).exists())
        self.assertEqual(File(path).size().in_bytes(), 0)

    def test_file_mode_create_raises_exception_when_file_already_exists(self):
        test_data = b"TEST_DATA_FILE_CONTENT"
        path = self.create_file("test-file", test_data)
        file = File(path)
        with self.assertRaises(CannotOpenFileException) as raised:
            file.open(FileMode.CREATE)

        self.assertIn("Failed to open file", str(raised.exception))
        self.assertIn("in mode 'CREATE'", str(raised.exception))
        self.assertIn("File exists", str(raised.exception))
        self.assertEqual(raised.exception.file_path, str(path))
        self.assertTrue(File(path).exists())
        self.assertFileContent(path, test_data)

    def test_file_mode_create_does_not_allow_read_and_write(self):
        path = self.create_path("test-file")
        file = File(path)
        file.open(FileMode.CREATE)
        with self.assertRaises(InvalidFileModeException) as raised:
            file.read()

        self.assertIn(
            "File is open in CREATE mode which does not allow reading",
            str(raised.exception)
        )
        self.assertEqual(raised.exception.file_path, str(path))

        with self.assertRaises(InvalidFileModeException) as raised:
            file.write(b"A")

        self.assertIn(
            "File is open in CREATE mode which does not allow writing",
            str(raised.exception)
        )
        self.assertEqual(raised.exception.file_path, str(path))

        file.close()
        self.assertTrue(File(path).exists())
        self.assertEqual(File(path).size().in_bytes(), 0)

    def test_file_mode_read(self):
        test_data = b"TEST_DATA_FILE_CONTENT"
        path = self.create_file("test-file", test_data)
        file = File(path)
        with file.open(FileMode.READ):
            read_data = file.read()

        self.assertEqual(read_data, test_data)

    def test_file_mode_read_raises_exception_when_file_does_not_exist(self):
        path = self.create_path("a-file-which-does-not-exist")
        file = File(path)
        with self.assertRaises(FileNotFoundException) as raised:
            file.open(FileMode.READ)

        self.assertIn("Failed to open file", str(raised.exception))
        self.assertIn("in mode 'READ'", str(raised.exception))
        self.assertIn("File does not exist", str(raised.exception))
        self.assertEqual(raised.exception.file_path, str(path))
        self.assertFileDoesNotExist(path)

    def test_file_mode_read_does_not_allow_write(self):
        test_data = b"TEST_DATA_FILE_CONTENT"
        path = self.create_file("test-file", test_data)
        file = File(path)
        file.open(FileMode.READ)
        with self.assertRaises(InvalidFileModeException) as raised:
            file.write(b"AAAA")

        file.close()
        self.assertIn(
            "File is open in READ mode which does not allow writing",
            str(raised.exception)
        )
        self.assertEqual(raised.exception.file_path, str(path))
        self.assertTrue(File(path).exists())
        self.assertFileContent(path, test_data)

    def test_file_mode_write(self):
        existing_data = b"TEST_DATA_FILE_CONTENT"
        data_to_write = b"AAAAAA"
        path = self.create_file("test-file", existing_data)
        file = File(path)
        with file.open(FileMode.WRITE):
            file.write(data_to_write)

        self.assertFileContent(path, data_to_write)

    def test_file_mode_write_when_file_does_not_already_exist(self):
        data_to_write = b"AAAAAA"
        path = self.create_path("new-test-file")
        file = File(path)
        with file.open(FileMode.WRITE):
            file.write(data_to_write)

        self.assertFileContent(path, data_to_write)

    def test_file_mode_write_does_not_allow_read(self):
        test_data = b"TEST_DATA_FILE_CONTENT"
        path = self.create_file("test-file", test_data)
        file = File(path)
        file.open(FileMode.WRITE)
        with self.assertRaises(InvalidFileModeException) as raised:
            file.read()

        file.close()
        self.assertIn(
            "File is open in WRITE mode which does not allow reading",
            str(raised.exception)
        )
        self.assertEqual(raised.exception.file_path, str(path))
        self.assertTrue(File(path).exists())
        self.assertFileContent(path, bytes())

    def test_file_mode_append(self):
        existing_data = b"TEST_DATA_FILE_CONTENT"
        data_to_append = b"AAAAAA"
        path = self.create_file("test-file", existing_data)
        file = File(path)
        with file.open(FileMode.APPEND):
            file.write(data_to_append)

        self.assertFileContent(path, existing_data + data_to_append)

    def test_file_mode_append_when_file_does_not_already_exist(self):
        data_to_append = b"AAAAAA"
        path = self.create_path("new-test-file")
        file = File(path)
        with file.open(FileMode.APPEND):
            file.write(data_to_append)

        self.assertFileContent(path, data_to_append)

    def test_file_mode_append_does_not_allow_read(self):
        test_data = b"TEST_DATA_FILE_CONTENT"
        path = self.create_file("test-file", test_data)
        file = File(path)
        file.open(FileMode.APPEND)
        with self.assertRaises(InvalidFileModeException) as raised:
            file.read()

        file.close()
        self.assertIn(
            "File is open in APPEND mode which does not allow reading",
            str(raised.exception)
        )
        self.assertEqual(raised.exception.file_path, str(path))
        self.assertTrue(File(path).exists())
        self.assertFileContent(path, test_data)

    def test_file_mode_read_write(self):
        existing_data = b"TEST_DATA_FILE_CONTENT"
        data_to_write = b"A" * len(existing_data)
        path = self.create_file("test-file", existing_data)
        file = File(path)
        with file.open(FileMode.READ_WRITE):
            read_data = file.read()
            file.rewind_position()
            file.write(data_to_write)

        self.assertEqual(read_data, existing_data)
        self.assertFileContent(path, data_to_write)

    def test_file_mode_read_write_raises_when_file_not_already_exist(self):
        path = self.create_path("a-test-file")
        file = File(path)
        with self.assertRaises(FileNotFoundException) as raised:
            file.open(FileMode.READ_WRITE)

        file.close()
        self.assertIn("Failed to open file", str(raised.exception))
        self.assertIn("File does not exist", str(raised.exception))
        self.assertEqual(raised.exception.file_path, str(path))
        self.assertFileDoesNotExist(path)

    def test_file_mode_read_append(self):
        existing_data = b"TEST_DATA_FILE_CONTENT"
        data_to_append = b"AAAAAA"
        path = self.create_file("test-file", existing_data)
        file = File(path)
        with file.open(FileMode.READ_APPEND):
            read_data = file.rewind_position().read()
            file.write(data_to_append)

        self.assertEqual(read_data, existing_data)
        self.assertFileContent(path, existing_data + data_to_append)

    def test_file_mode_read_append_when_file_does_not_already_exist(self):
        test_data = b"TEST_DATA_FILE_CONTENT"
        path = self.create_path("test-file")
        file = File(path)
        with file.open(FileMode.READ_APPEND):
            read_data = file.read()
            file.write(test_data)

        self.assertEqual(read_data, bytes())
        self.assertTrue(File(path).exists())
        self.assertFileContent(path, test_data)

    def test_file_mode_create_write(self):
        test_data = b"TEST_DATA_FILE_CONTENT"
        path = self.create_path("test-file")
        file = File(path)
        with file.open(FileMode.CREATE_WRITE):
            file.write(test_data)

        self.assertFileContent(path, test_data)

    def test_file_mode_create_write_raises_when_file_already_exists(self):
        test_data = b"TEST_DATA_FILE_CONTENT"
        path = self.create_file("a-test-file", test_data)
        file = File(path)
        with self.assertRaises(CannotOpenFileException) as raised:
            file.open(FileMode.CREATE_WRITE)

        file.close()
        self.assertIn("Failed to open file", str(raised.exception))
        self.assertIn("in mode 'CREATE_WRITE", str(raised.exception))
        self.assertIn("File exists", str(raised.exception))
        self.assertEqual(raised.exception.file_path, str(path))
        self.assertTrue(File(path).exists())
        self.assertFileContent(path, test_data)

    def test_file_mode_create_write_does_not_allow_read(self):
        path = self.create_path("a-test-file")
        file = File(path)
        file.open(FileMode.CREATE_WRITE)
        with self.assertRaises(InvalidFileModeException) as raised:
            file.read()

        file.close()
        self.assertIn("Cannot read from file", str(raised.exception))
        self.assertIn(
            "File is open in CREATE_WRITE mode which does not allow reading",
            str(raised.exception)
        )
        self.assertEqual(raised.exception.file_path, str(path))
        self.assertTrue(File(path).exists())

    def test_file_mode_create_read_write(self):
        test_data = b"TEST_DATA_FILE_CONTENT"
        path = self.create_path("test-file")
        file = File(path)
        with file.open(FileMode.CREATE_READ_WRITE):
            file.write(test_data)
            file.flush()
            file.rewind_position()
            read_data = file.read()

        self.assertEqual(read_data, test_data)
        self.assertFileContent(path, test_data)

    def test_file_mode_create_read_write_when_file_already_exists(self):
        test_data = b"TEST_DATA_FILE_CONTENT"
        path = self.create_file("a-test-file", b"ORIGINAL_FILE_DATA")
        file = File(path)
        with file.open(FileMode.CREATE_READ_WRITE):
            file.write(test_data)
            file.flush()
            file.rewind_position()
            read_data = file.read()

        self.assertEqual(read_data, test_data)
        self.assertTrue(File(path).exists())
        self.assertFileContent(path, test_data)

    def test_opening_an_already_open_file_raises_exception(self):
        file = File(self.create_file("test-file"))
        file.open()
        with self.assertRaises(InvalidFileStateException) as raised:
            file.open()

        self.assertIn("Is already open", str(raised.exception))
        self.assertEqual(raised.exception.file_path, str(file.path))

    def test_can_read_bytes_from_file(self):
        test_data = b"TEST_DATA_FILE_CONTENT"
        file = File(self.create_file("test-file", test_data))
        file.open()
        file_data = file.read()
        file.close()
        self.assertEqual(file_data, test_data)

    def test_reading_bytes_from_closed_file_raises_exception(self):
        test_data = b"TEST_DATA_FILE_CONTENT"
        file = File(self.create_file("test-file", test_data))
        with self.assertRaises(InvalidFileStateException) as raised:
            file.read()

        self.assertIn(
            "must be opened before read operation", str(raised.exception)
        )
        self.assertEqual(raised.exception.file_path, str(file.path))

    def test_can_read_partial_bytes_from_file(self):
        test_data = b"TEST_DATA_FILE_CONTENT"
        file = File(self.create_file("test-file", test_data))
        file.open()
        file_data = file.read(n_bytes=9)
        file.close()
        self.assertEqual(file_data, test_data[:9])

    def test_can_read_all_bytes_from_file(self):
        test_data = b"TEST_DATA_FILE_CONTENT"
        file = File(self.create_file("test-file", test_data))
        with file.open():
            file_data = file.read(FILE_READ_ALL)

        self.assertEqual(file_data, test_data)

    def test_can_read_text_from_file(self):
        test_text = "TEST_DATA_FILE_CONTENT"
        file = File(self.create_file("test-file", test_text))
        file.open()
        file_text = file.read_text()
        file.close()
        self.assertEqual(file_text, test_text)

    def test_can_read_partial_text_from_file(self):
        test_text = "TEST_DATA_FILE_CONTENT"
        file = File(self.create_file("test-file", test_text))
        file.open()
        file_text = file.read_text(n_bytes=9)
        file.close()
        self.assertEqual(file_text, test_text[:9])

    def test_can_read_partial_text_with_truncated_code_point_from_file(self):
        test_text = "TEST_DATA_with_A🙃A_FILE_CONTENT"
        file = File(self.create_file("test-file", test_text))
        with file.open():
            file_text_1 = file.read_text(n_bytes=16)

        with file.open():
            file_text_2 = file.read_text(n_bytes=17)

        with file.open():
            file_text_3 = file.read_text(n_bytes=18)

        with file.open():
            file_text_4 = file.read_text(n_bytes=19)

        with file.open():
            file_text_5 = file.read_text(n_bytes=20)

        with file.open():
            file_text_6 = file.read_text(n_bytes=21)

        self.assertEqual(file_text_1, test_text[:16])
        self.assertEqual(file_text_2, test_text[:17])
        self.assertEqual(file_text_3, test_text[:17])
        self.assertEqual(file_text_4, test_text[:17])
        self.assertEqual(file_text_5, test_text[:17])
        self.assertEqual(file_text_6, test_text[:18])

    def test_reading_text_with_invalid_truncated_code_point_raises_ex(self):
        # 🙃 := f0 9f 99 83
        file_1 = File(
            self.create_file("test-file-1", b"TEST_DATA_with_A\xf0\x9f\x99")
        )
        file_2 = File(
            self.create_file("test-file-1", b"TEST_DATA_with_A\xf0\x9f")
        )
        file_3 = File(
            self.create_file("test-file-1", b"TEST_DATA_with_A\xf0")
        )
        with self.assertRaises(FileTextDecodeException) as raised:
            with file_1.open():
                file_1.read_text(n_bytes=FILE_READ_ALL)

        self.assertIn(
            "Failed to decode UTF-8 text while reading file",
            str(raised.exception)
        )
        self.assertIn("unexpected end of data", str(raised.exception))
        self.assertEqual(raised.exception.file_path, str(file_1.path))

        with self.assertRaises(FileTextDecodeException) as raised:
            file_2.read_all_text()

        self.assertIn(
            "Failed to decode UTF-8 text while reading file",
            str(raised.exception)
        )
        self.assertIn("unexpected end of data", str(raised.exception))
        self.assertEqual(raised.exception.file_path, str(file_2.path))

        with self.assertRaises(FileTextDecodeException) as raised:
            with file_3.open():
                file_3.read_text(n_bytes=FILE_READ_ALL)

        self.assertIn(
            "Failed to decode UTF-8 text while reading file",
            str(raised.exception)
        )
        self.assertIn("unexpected end of data", str(raised.exception))
        self.assertEqual(raised.exception.file_path, str(file_3.path))

    def test_can_write_bytes_to_file(self):
        test_data = b"TEST_DATA_FILE_CONTENT"
        file = File(self.create_path("test-file"))
        file.open(FileMode.CREATE_WRITE)
        n_bytes_written = file.write(test_data)
        file.close()
        self.assertIsInstance(n_bytes_written, int)
        self.assertEqual(n_bytes_written, len(test_data))
        self.assertFileContent(file.path, test_data)

    def test_can_write_bytearray_to_file(self):
        test_data = bytearray(b"TEST_DATA_FILE_CONTENT")
        file = File(self.create_path("test-file"))
        file.open(FileMode.CREATE_WRITE)
        n_bytes_written = file.write(test_data)
        file.close()
        self.assertIsInstance(n_bytes_written, int)
        self.assertEqual(n_bytes_written, len(test_data))
        self.assertFileContent(file.path, test_data)

    def test_can_write_text_to_file(self):
        test_data = "TEST_DATA_FILE_CONTENT"
        file = File(self.create_path("test-file"))
        file.open(FileMode.CREATE_WRITE)
        n_bytes_written = file.write(test_data)
        file.close()
        self.assertIsInstance(n_bytes_written, int)
        self.assertEqual(n_bytes_written, len(test_data))
        self.assertFileContent(file.path, test_data)

    def test_can_write_text_with_custom_encoding_to_file(self):
        test_data = "TEST_DATA_FILE_CONTENT"
        test_encoding = "UTF-16LE"
        file = File(self.create_path("test-file"))
        file.text_encoding = test_encoding
        file.open(FileMode.CREATE_WRITE)
        n_bytes_written = file.write(test_data)
        file.close()
        self.assertIsInstance(n_bytes_written, int)
        self.assertEqual(n_bytes_written, len(test_data.encode(test_encoding)))
        self.assertFileContent(file.path, test_data.encode(test_encoding))

    def test_writing_bytes_to_closed_file_raises_exception(self):
        test_data = b"TEST_DATA_FILE_CONTENT"
        file = File(self.create_file("test-file"))
        with self.assertRaises(InvalidFileStateException) as raised:
            file.write(test_data)

        self.assertIn(
            "must be opened before write operation", str(raised.exception)
        )
        self.assertEqual(raised.exception.file_path, str(file.path))

    def test_writing_text_with_invalid_encoding_to_file_raises_exception(self):
        test_data = "TEST_DATA_FILE_CONTENT"
        file = File(self.create_path("test-file"))
        file.text_encoding = "AN-INVALID-ENCODING"
        file.open(FileMode.CREATE_WRITE)
        with self.assertRaises(FileTextEncodeException) as raised:
            file.write(test_data)

        self.assertIn(
            "Failed to encode text while trying to write to file",
            str(raised.exception)
        )
        self.assertIn(
            f"Invalid encoding '{file.text_encoding}'",
            str(raised.exception)
        )
        self.assertEqual(raised.exception.file_path, str(file.path))

    def test_read_text_file_with_lf_line_separator(self):
        test_data = b"TEST\nDATA\nFILE\nCONTENT"
        path = self.create_file("test-text-file.txt", test_data)
        file = File(path)
        read_text = file.read_all_text()
        self.assertIsInstance(read_text, str)
        self.assertEqual(read_text, "TEST\nDATA\nFILE\nCONTENT")

    def test_read_lines_from_text_file_with_lf_line_separator(self):
        test_data = b"TEST\nDATA\nFILE\nCONTENT"
        path = self.create_file("test-text-file.txt", test_data)
        file = File(path)
        read_lines = file.read_all_text_lines()
        self.assertIsInstance(read_lines, list)
        self.assertEqual(len(read_lines), 4)
        self.assertEqual(read_lines[0], "TEST")
        self.assertEqual(read_lines[1], "DATA")
        self.assertEqual(read_lines[2], "FILE")
        self.assertEqual(read_lines[3], "CONTENT")

    def test_read_text_file_with_cr_lf_line_separator(self):
        test_data = b"TEST\r\nDATA\r\nFILE\r\nCONTENT"
        path = self.create_file("test-text-file.txt", test_data)
        file = File(path)
        read_text = file.read_all_text()
        self.assertIsInstance(read_text, str)
        self.assertEqual(read_text, "TEST\nDATA\nFILE\nCONTENT")

    def test_read_lines_from_text_file_with_cr_lf_line_separator(self):
        test_data = b"TEST\r\nDATA\r\nFILE\r\nCONTENT"
        path = self.create_file("test-text-file.txt", test_data)
        file = File(path)
        read_lines = file.read_all_text_lines()
        self.assertIsInstance(read_lines, list)
        self.assertEqual(len(read_lines), 4)
        self.assertEqual(read_lines[0], "TEST")
        self.assertEqual(read_lines[1], "DATA")
        self.assertEqual(read_lines[2], "FILE")
        self.assertEqual(read_lines[3], "CONTENT")

    def test_read_text_file_with_cr_line_separator(self):
        test_data = b"TEST\rDATA\rFILE\rCONTENT"
        path = self.create_file("test-text-file.txt", test_data)
        file = File(path)
        read_text = file.read_all_text()
        self.assertIsInstance(read_text, str)
        self.assertEqual(read_text, "TEST\nDATA\nFILE\nCONTENT")

    def test_read_lines_from_text_file_with_cr_line_separator(self):
        test_data = b"TEST\rDATA\rFILE\rCONTENT"
        path = self.create_file("test-text-file.txt", test_data)
        file = File(path)
        read_lines = file.read_all_text_lines()
        self.assertIsInstance(read_lines, list)
        self.assertEqual(len(read_lines), 4)
        self.assertEqual(read_lines[0], "TEST")
        self.assertEqual(read_lines[1], "DATA")
        self.assertEqual(read_lines[2], "FILE")
        self.assertEqual(read_lines[3], "CONTENT")

    def test_write_text_file_with_lf_line_separator(self):
        test_text = "TEST\nDATA\nFILE\nCONTENT"
        path = self.create_path("test-text-file.txt")
        file = File(path)
        file.line_separator = "\n"
        n_bytes_written = file.write_all(test_text)
        self.assertEqual(n_bytes_written, 22)
        self.assertTrue(File(path).exists())
        self.assertFileContent(path, b"TEST\nDATA\nFILE\nCONTENT")

    def test_write_text_file_with_cr_lf_line_separator(self):
        test_text = "TEST\nDATA\nFILE\nCONTENT"
        path = self.create_path("test-text-file.txt")
        file = File(path)
        file.line_separator = "\r\n"
        n_bytes_written = file.write_all(test_text)
        self.assertEqual(n_bytes_written, 25)
        self.assertTrue(File(path).exists())
        self.assertFileContent(path, b"TEST\r\nDATA\r\nFILE\r\nCONTENT")

    def test_write_text_file_with_cr_line_separator(self):
        test_text = "TEST\nDATA\nFILE\nCONTENT"
        path = self.create_path("test-text-file.txt")
        file = File(path)
        file.line_separator = "\r"
        n_bytes_written = file.write_all(test_text)
        self.assertEqual(n_bytes_written, 22)
        self.assertTrue(File(path).exists())
        self.assertFileContent(path, b"TEST\rDATA\rFILE\rCONTENT")

    def test_reading_and_writing_text_with_line_separator(self):
        test_text = "\nTEST\nDATA\nFILE\nCONTENT\n"
        path = self.create_path("test-text-file.txt")
        with File(path).open(FileMode.WRITE) as file:
            n_bytes_written = file.write(test_text)

        self.assertTrue(File(path).exists())
        if self.sys_win32:
            self.assertEqual(n_bytes_written, 29)
            self.assertFileContent(
                path,
                b"\r\nTEST\r\nDATA\r\nFILE\r\nCONTENT\r\n"
            )
        else:
            self.assertEqual(n_bytes_written, 24)
            self.assertFileContent(path, b"\nTEST\nDATA\nFILE\nCONTENT\n")

        with File(path).open(FileMode.READ) as file:
            read_text = file.read_text()

        self.assertIsInstance(read_text, str)
        self.assertEqual(read_text, test_text)

    def test_can_flush_file(self):
        test_data = b"TEST_DATA_FILE_CONTENT"
        path = self.create_path("test-file")
        file = File(path)
        file.open(FileMode.CREATE_WRITE)
        file.write(test_data)
        self.assertFileContent(path, bytes())
        file.flush()
        self.assertFileContent(path, test_data)
        file.close()
        self.assertFileContent(path, test_data)

    def test_flushing_closed_file_raises_exception(self):
        path = self.create_path("test-file")
        file = File(path)
        with self.assertRaises(InvalidFileStateException) as raised:
            file.flush()

        self.assertIn(
            "must be opened before flush operation", str(raised.exception)
        )
        self.assertEqual(raised.exception.file_path, str(path))

    def test_get_position(self):
        test_data = b"TEST_DATA_FILE_CONTENT"
        path = self.create_file("test-file", test_data)
        file = File(path)
        with file.open(FileMode.READ_WRITE):
            position = file.position()
            self.assertEqual(position, FILE_POSITION_BEGIN)
            file.read(FILE_READ_ALL)
            position = file.position()
            self.assertEqual(position, file.size().value)
            file.rewind_position().read(8)
            position = file.position()
            self.assertEqual(position, 8)

        self.assertFileContent(path, test_data)

    def test_set_position(self):
        test_data = b"TEST_DATA_FILE_CONTENT"
        path = self.create_file("test-file", test_data)
        file = File(path)
        with file.open(FileMode.READ_WRITE):
            file.set_position(15)
            position = file.position()
            self.assertEqual(position, 15)
            file.write(b"POSITION")
            position = file.position()
            self.assertEqual(position, 23)
            file.set_position(5)
            read_data = file.read(FILE_READ_ALL)
            self.assertEqual(read_data, b"DATA_FILE_POSITION")
            position = file.position()
            self.assertEqual(position, 23)

        self.assertFileContent(path, b"TEST_DATA_FILE_POSITION")

    def test_rewind_position(self):
        test_data = b"TEST_DATA_FILE_CONTENT"
        path = self.create_file("test-file", test_data)
        file = File(path)
        with file.open(FileMode.READ_APPEND):
            position = file.position()
            self.assertEqual(position, len(test_data))
            file.rewind_position()
            position = file.position()
            self.assertEqual(position, FILE_POSITION_BEGIN)
            file.rewind_position()
            # Test can be called multiple times
            self.assertEqual(position, FILE_POSITION_BEGIN)

        self.assertFileContent(path, test_data)

    def test_resize_regular_file_to_smaller_size(self):
        test_data = b"TEST_DATA_FILE_CONTENT"
        path = self.create_file("test-file", test_data)
        file = File(path)
        with file.open(FileMode.READ_WRITE):
            file.resize(FileSize(9, FileSizeUnit.BYTE))

        self.assertTrue(File(path).exists())
        self.assertEqual(File(path).size().in_bytes(), 9)
        self.assertFileContent(path, test_data[:9])

    def test_resize_regular_file_to_larger_size(self):
        test_data = b"TEST_DATA_FILE_CONTENT"
        path = self.create_file("test-file", test_data)
        file = File(path)
        with file.open(FileMode.READ_WRITE):
            file.resize(FileSize(32, FileSizeUnit.BYTE))

        self.assertTrue(File(path).exists())
        self.assertEqual(File(path).size().in_bytes(), 32)
        self.assertFileContent(path, test_data + (b"\x00" * 10))

    def test_resize_regular_file_at_position_indicator(self):
        test_data = b"TEST_DATA_FILE_CONTENT"
        path = self.create_file("test-file", test_data)
        file = File(path)
        with file.open(FileMode.READ_WRITE):
            file.set_position(8)
            file.resize(FILE_RESIZE_TO_CURRENT_POSITION)

        self.assertTrue(File(path).exists())
        self.assertEqual(File(path).size().in_bytes(), 8)
        self.assertFileContent(path, test_data[:8])

    def test_resize_regular_file_with_implicit_size_conversion(self):
        test_data = "A" * int(5.123 * 10**3)  # 5.123KB
        path = self.create_file("test-file", test_data)
        file = File(path)
        target_size = FileSize(2.2, FileSizeUnit.KILOBYTE)
        with file.open(FileMode.READ_WRITE):
            file.resize(target_size)

        self.assertTrue(File(path).exists())
        target_size_in_bytes = target_size.in_bytes()
        self.assertEqual(File(path).size().in_bytes(), target_size_in_bytes)
        self.assertFileContent(path, test_data[:target_size_in_bytes])

    def test_attempting_to_resize_closed_file_raises_exception(self):
        test_data = b"TEST_DATA_FILE_CONTENT"
        path = self.create_file("test-file", test_data)
        file = File(path)
        self.assertFalse(file.is_open())
        with self.assertRaises(InvalidFileStateException) as raised:
            file.resize(FileSize(32, FileSizeUnit.BYTE))

        self.assertFalse(file.is_open())
        self.assertIn("Cannot resize file", str(raised.exception))
        self.assertIn(
            "File must be opened before resize operation",
            str(raised.exception)
        )
        self.assertEqual(raised.exception.file_path, str(path))
        self.assertTrue(File(path).exists())

    def test_attempting_to_resize_file_opened_in_read_mode_raises_ex(self):
        test_data = b"TEST_DATA_FILE_CONTENT"
        path = self.create_file("test-file", test_data)
        file = File(path)
        file.open(FileMode.READ)
        with self.assertRaises(InvalidFileModeException) as raised:
            file.resize(FileSize(32, FileSizeUnit.BYTE))

        file.close()
        self.assertFalse(file.is_open())
        self.assertIn("Cannot resize file", str(raised.exception))
        self.assertIn(
            "File is open in READ mode which does not allow writing",
            str(raised.exception)
        )
        self.assertEqual(raised.exception.file_path, str(path))
        self.assertTrue(File(path).exists())

    def test_query_file_access_on_regular_file(self):
        path = self.create_file("test-file")
        file = File(path)
        file.set_permission(FilePermission.of(owner=FileAccess.no_access()))
        access = file.access()
        self.assertIsInstance(access, FileAccess)
        self.assertFalse(access.can_read)
        self.assertFalse(access.can_write)
        self.assertFalse(access.can_execute)
        file.set_permission(
            FilePermission.of(owner=FileAccess.of(executable=True))
        )
        access = file.access()
        self.assertFalse(access.can_read)
        self.assertFalse(access.can_write)
        self.assertTrue(access.can_execute)
        file.set_permission(
            FilePermission.of(owner=FileAccess.of(writable=True))
        )
        access = file.access()
        self.assertFalse(access.can_read)
        self.assertTrue(access.can_write)
        self.assertFalse(access.can_execute)
        file.set_permission(
            FilePermission.of(
                owner=FileAccess.of(writable=True, executable=True)
            )
        )
        access = file.access()
        self.assertFalse(access.can_read)
        self.assertTrue(access.can_write)
        self.assertTrue(access.can_execute)
        file.set_permission(
            FilePermission.of(owner=FileAccess.of(readable=True))
        )
        access = file.access()
        self.assertTrue(access.can_read)
        self.assertFalse(access.can_write)
        self.assertFalse(access.can_execute)
        file.set_permission(
            FilePermission.of(
                owner=FileAccess.of(readable=True, executable=True)
            )
        )
        access = file.access()
        self.assertTrue(access.can_read)
        self.assertFalse(access.can_write)
        self.assertTrue(access.can_execute)
        file.set_permission(
            FilePermission.of(
                owner=FileAccess.of(readable=True, writable=True)
            )
        )
        access = file.access()
        self.assertTrue(access.can_read)
        self.assertTrue(access.can_write)
        self.assertFalse(access.can_execute)
        file.set_permission(FilePermission.of(owner=FileAccess.all_access()))
        access = file.access()
        self.assertTrue(access.can_read)
        self.assertTrue(access.can_write)
        self.assertTrue(access.can_execute)

    def test_query_file_access_on_directory(self):
        path = self.create_directory("test-dir")
        file = File(path)
        file.set_permission(FilePermission.of(owner=FileAccess.no_access()))
        access = file.access()
        self.assertIsInstance(access, FileAccess)
        self.assertFalse(access.can_read)
        self.assertFalse(access.can_write)
        self.assertFalse(access.can_execute)
        file.set_permission(
            FilePermission.of(owner=FileAccess.of(executable=True))
        )
        access = file.access()
        self.assertFalse(access.can_read)
        self.assertFalse(access.can_write)
        self.assertTrue(access.can_execute)
        file.set_permission(
            FilePermission.of(owner=FileAccess.of(writable=True))
        )
        access = file.access()
        self.assertFalse(access.can_read)
        self.assertTrue(access.can_write)
        self.assertFalse(access.can_execute)
        file.set_permission(
            FilePermission.of(
                owner=FileAccess.of(writable=True, executable=True)
            )
        )
        access = file.access()
        self.assertFalse(access.can_read)
        self.assertTrue(access.can_write)
        self.assertTrue(access.can_execute)
        file.set_permission(
            FilePermission.of(owner=FileAccess.of(readable=True))
        )
        access = file.access()
        self.assertTrue(access.can_read)
        self.assertFalse(access.can_write)
        self.assertFalse(access.can_execute)
        file.set_permission(
            FilePermission.of(
                owner=FileAccess.of(readable=True, executable=True)
            )
        )
        access = file.access()
        self.assertTrue(access.can_read)
        self.assertFalse(access.can_write)
        self.assertTrue(access.can_execute)
        file.set_permission(
            FilePermission.of(
                owner=FileAccess.of(readable=True, writable=True)
            )
        )
        access = file.access()
        self.assertTrue(access.can_read)
        self.assertTrue(access.can_write)
        self.assertFalse(access.can_execute)
        file.set_permission(FilePermission.of(owner=FileAccess.all_access()))
        access = file.access()
        self.assertTrue(access.can_read)
        self.assertTrue(access.can_write)
        self.assertTrue(access.can_execute)

    def test_file_access_on_nonexistent_file_raises_ex(self):
        path = self.create_path("this-file-does-not-exist")
        file = File(path)
        with self.assertRaises(FileNotFoundException) as raised:
            file.access()

        self.assertIn(
            "Failed to obtain access capabilities for file",
            str(raised.exception)
        )
        self.assertIn("No such file or directory", str(raised.exception))
        self.assertEqual(raised.exception.file_path, str(file.path))

    def test_query_file_is_readable(self):
        path = self.create_file("test-file")
        file = File(path)
        file.set_permission(FilePermission.of(owner=FileAccess.no_access()))
        self.assertIsInstance(file.is_readable(), bool)
        self.assertFalse(file.is_readable())
        file.set_permission(
            FilePermission.of(owner=FileAccess.of(executable=True))
        )
        self.assertFalse(file.is_readable())
        file.set_permission(
            FilePermission.of(owner=FileAccess.of(writable=True))
        )
        self.assertFalse(file.is_readable())
        file.set_permission(
            FilePermission.of(
                owner=FileAccess.of(writable=True, executable=True)
            )
        )
        self.assertFalse(file.is_readable())
        file.set_permission(
            FilePermission.of(owner=FileAccess.of(readable=True))
        )
        self.assertTrue(file.is_readable())
        file.set_permission(
            FilePermission.of(
                owner=FileAccess.of(readable=True, executable=True)
            )
        )
        self.assertTrue(file.is_readable())
        file.set_permission(
            FilePermission.of(
                owner=FileAccess.of(readable=True, writable=True)
            )
        )
        self.assertTrue(file.is_readable())
        file.set_permission(FilePermission.of(owner=FileAccess.all_access()))
        self.assertTrue(file.is_readable())

    def test_query_file_is_readable_returns_false_for_nonexistent_file(self):
        path = self.create_path("this-file-does-not-exist")
        self.assertFalse(File(path).is_readable())

    def test_query_file_is_writable(self):
        path = self.create_file("test-file")
        file = File(path)
        file.set_permission(FilePermission.of(owner=FileAccess.no_access()))
        self.assertIsInstance(file.is_writable(), bool)
        self.assertFalse(file.is_writable())
        file.set_permission(
            FilePermission.of(owner=FileAccess.of(executable=True))
        )
        self.assertFalse(file.is_writable())
        file.set_permission(
            FilePermission.of(owner=FileAccess.of(writable=True))
        )
        self.assertTrue(file.is_writable())
        file.set_permission(
            FilePermission.of(
                owner=FileAccess.of(writable=True, executable=True)
            )
        )
        self.assertTrue(file.is_writable())
        file.set_permission(
            FilePermission.of(owner=FileAccess.of(readable=True))
        )
        self.assertFalse(file.is_writable())
        file.set_permission(
            FilePermission.of(
                owner=FileAccess.of(readable=True, executable=True)
            )
        )
        self.assertFalse(file.is_writable())
        file.set_permission(
            FilePermission.of(
                owner=FileAccess.of(readable=True, writable=True)
            )
        )
        self.assertTrue(file.is_writable())
        file.set_permission(FilePermission.of(owner=FileAccess.all_access()))
        self.assertTrue(file.is_writable())

    def test_query_file_is_writable_returns_false_for_nonexistent_file(self):
        path = self.create_path("this-file-does-not-exist")
        self.assertFalse(File(path).is_writable())

    def test_query_file_is_executable(self):
        path = self.create_file("test-file")
        file = File(path)
        file.set_permission(FilePermission.of(owner=FileAccess.no_access()))
        self.assertIsInstance(file.is_executable(), bool)
        self.assertFalse(file.is_executable())
        file.set_permission(
            FilePermission.of(owner=FileAccess.of(executable=True))
        )
        self.assertTrue(file.is_executable())
        file.set_permission(
            FilePermission.of(owner=FileAccess.of(writable=True))
        )
        self.assertFalse(file.is_executable())
        file.set_permission(
            FilePermission.of(
                owner=FileAccess.of(writable=True, executable=True)
            )
        )
        self.assertTrue(file.is_executable())
        file.set_permission(
            FilePermission.of(owner=FileAccess.of(readable=True))
        )
        self.assertFalse(file.is_executable())
        file.set_permission(
            FilePermission.of(
                owner=FileAccess.of(readable=True, executable=True)
            )
        )
        self.assertTrue(file.is_executable())
        file.set_permission(
            FilePermission.of(
                owner=FileAccess.of(readable=True, writable=True)
            )
        )
        self.assertFalse(file.is_executable())
        file.set_permission(FilePermission.of(owner=FileAccess.all_access()))
        self.assertTrue(file.is_executable())

    def test_query_file_is_executable_returns_false_for_nonexistent_file(self):
        path = self.create_path("this-file-does-not-exist")
        self.assertFalse(File(path).is_executable())

    def test_can_get_file_permission_of_regular_file(self):
        path = self.create_file("test-file")
        file = File(path)
        permission = file.permission()
        self.assertIsInstance(permission, FilePermission)
        self.assertEqual(str(permission), "rw-rw-r--")
        perm_owner = permission.owner
        perm_group = permission.group
        perm_other = permission.other
        self.assertIsInstance(perm_owner, FileAccess)
        self.assertIsInstance(perm_group, FileAccess)
        self.assertIsInstance(perm_other, FileAccess)
        self.assertEqual(str(perm_owner), "rw-")
        self.assertEqual(str(perm_group), "rw-")
        self.assertEqual(str(perm_other), "r--")
        self.assertTrue(perm_owner.can_read)
        self.assertTrue(perm_owner.can_write)
        self.assertFalse(perm_owner.can_execute)
        self.assertTrue(perm_group.can_read)
        self.assertTrue(perm_group.can_write)
        self.assertFalse(perm_group.can_execute)
        self.assertTrue(perm_other.can_read)
        self.assertFalse(perm_other.can_write)
        self.assertFalse(perm_other.can_execute)

    def test_can_get_file_permission_of_directory(self):
        path = self.create_directory("test-dir")
        file = File(path)
        permission = file.permission()
        self.assertIsInstance(permission, FilePermission)
        self.assertEqual(str(permission), "rwxrwxr-x")
        perm_owner = permission.owner
        perm_group = permission.group
        perm_other = permission.other
        self.assertIsInstance(perm_owner, FileAccess)
        self.assertIsInstance(perm_group, FileAccess)
        self.assertIsInstance(perm_other, FileAccess)
        self.assertEqual(str(perm_owner), "rwx")
        self.assertEqual(str(perm_group), "rwx")
        self.assertEqual(str(perm_other), "r-x")
        self.assertTrue(perm_owner.can_read)
        self.assertTrue(perm_owner.can_write)
        self.assertTrue(perm_owner.can_execute)
        self.assertTrue(perm_group.can_read)
        self.assertTrue(perm_group.can_write)
        self.assertTrue(perm_group.can_execute)
        self.assertTrue(perm_other.can_read)
        self.assertFalse(perm_other.can_write)
        self.assertTrue(perm_other.can_execute)

    def test_getting_permission_of_nonexistent_file_raises_exception(self):
        file = File(self.create_path("nonexistent-file"))
        with self.assertRaises(FileNotFoundException) as raised:
            file.permission()

        self.assertIn(
            "Failed to read file permission for file",
            str(raised.exception)
        )
        self.assertIn("File does not exist", str(raised.exception))
        self.assertEqual(raised.exception.file_path, str(file.path))

    def test_can_set_file_permission_of_regular_file(self):
        path = self.create_file("test-file")
        file = File(path)
        file.set_permission(
            FilePermission.of(
                owner=FileAccess.of(readable=True),
                group=FileAccess.no_access(),
                other=FileAccess.no_access()
            )
        )
        permission = file.permission()
        self.assertEqual(str(permission), "r--------")
        self.assertTrue(permission.owner.can_read)
        self.assertFalse(permission.owner.can_write)
        self.assertFalse(permission.owner.can_execute)
        self.assertFalse(permission.group.can_read)
        self.assertFalse(permission.group.can_write)
        self.assertFalse(permission.group.can_execute)
        self.assertFalse(permission.other.can_read)
        self.assertFalse(permission.other.can_write)
        self.assertFalse(permission.other.can_execute)
        file.set_permission(
            FilePermission.of(
                owner=FileAccess.of(readable=True, writable=True),
                group=FileAccess.of(executable=True),
                other=FileAccess.of(readable=True)
            )
        )
        permission = File(path).permission()
        self.assertEqual(str(permission), "rw---xr--")
        file.set_permission(
            FilePermission.of(
                owner=FileAccess.all_access(),
                group=FileAccess.all_access(),
                other=FileAccess.all_access()
            )
        )
        permission = File(path).permission()
        self.assertEqual(str(permission), "rwxrwxrwx")

    def test_can_set_file_permission_of_directory(self):
        path = self.create_directory("test-dir")
        file = File(path)
        file.set_permission(
            FilePermission.of(
                owner=FileAccess.of(readable=True, writable=True),
                group=FileAccess.of(readable=True),
                other=FileAccess.of(readable=True)
            )
        )
        permission = file.permission()
        self.assertEqual(str(permission), "rw-r--r--")
        self.assertTrue(permission.owner.can_read)
        self.assertTrue(permission.owner.can_write)
        self.assertFalse(permission.owner.can_execute)
        self.assertTrue(permission.group.can_read)
        self.assertFalse(permission.group.can_write)
        self.assertFalse(permission.group.can_execute)
        self.assertTrue(permission.other.can_read)
        self.assertFalse(permission.other.can_write)
        self.assertFalse(permission.other.can_execute)

        permission.group.can_write = True
        file.set_permission(permission)
        permission = File(path).permission()
        self.assertEqual(str(permission), "rw-rw-r--")
        permission.owner.can_execute = True
        permission.group.can_execute = True
        permission.other.can_execute = True
        file.set_permission(permission)
        permission = File(path).permission()
        self.assertEqual(str(permission), "rwxrwxr-x")
        permission = FilePermission.of(
            owner=FileAccess.all_access(),
            group=FileAccess.all_access(),
            other=FileAccess.all_access()
        )
        file.set_permission(permission)
        permission = File(path).permission()
        self.assertEqual(str(permission), "rwxrwxrwx")

    def test_setting_permission_of_nonexistent_file_raises_exception(self):
        file = File(self.create_path("nonexistent-file"))
        with self.assertRaises(FileNotFoundException) as raised:
            file.set_permission(
                FilePermission.of(
                    owner=FileAccess.all_access(),
                    group=FileAccess.all_access(),
                    other=FileAccess.all_access()
                )
            )

        self.assertIn(
            "Failed to set file permission to",
            str(raised.exception)
        )
        self.assertIn("File does not exist", str(raised.exception))
        self.assertEqual(raised.exception.file_path, str(file.path))

    def test_can_get_owner_uid_of_regular_file(self):
        path = self.create_file("test-file")
        file = File(path)
        file_uid = file.owner()
        self.assertEqual(file_uid, 1000)

    def test_can_get_owner_uid_of_directory(self):
        path = self.create_directory("test-dir")
        file = File(path)
        file_uid = file.owner()
        self.assertEqual(file_uid, 1000)

    def test_getting_owner_uid_of_nonexistent_file_raises_exception(self):
        file = File(self.create_path("nonexistent-file"))
        with self.assertRaises(FileNotFoundException) as raised:
            file.owner()

        self.assertIn(
            "Failed to get file owner UID for file",
            str(raised.exception)
        )
        self.assertIn("File does not exist", str(raised.exception))
        self.assertEqual(raised.exception.file_path, str(file.path))

    def test_can_get_owner_name_of_regular_file(self):
        path = self.create_file("test-file")
        file = File(path)
        file_owner_name = file.owner_name()
        self.assertEqual(file_owner_name, "user")

    def test_can_get_owner_name_of_directory(self):
        path = self.create_directory("test-dir")
        file = File(path)
        file_owner_name = file.owner_name()
        self.assertEqual(file_owner_name, "user")

    def test_getting_owner_name_of_nonexistent_file_raises_exception(self):
        file = File(self.create_path("nonexistent-file"))
        with self.assertRaises(FileNotFoundException) as raised:
            file.owner_name()

        self.assertIn(
            "Failed to get file owner name for file",
            str(raised.exception)
        )
        self.assertIn("File does not exist", str(raised.exception))
        self.assertEqual(raised.exception.file_path, str(file.path))

    def test_can_get_group_gid_of_regular_file(self):
        path = self.create_file("test-file")
        file = File(path)
        file_gid = file.group()
        self.assertEqual(file_gid, 1000)

    def test_can_get_group_gid_of_directory(self):
        path = self.create_directory("test-dir")
        file = File(path)
        file_gid = file.group()
        self.assertEqual(file_gid, 1000)

    def test_getting_group_uid_of_nonexistent_file_raises_exception(self):
        file = File(self.create_path("nonexistent-file"))
        with self.assertRaises(FileNotFoundException) as raised:
            file.group()

        self.assertIn(
            "Failed to get file group GID for file",
            str(raised.exception)
        )
        self.assertIn("File does not exist", str(raised.exception))
        self.assertEqual(raised.exception.file_path, str(file.path))

    def test_can_get_group_name_of_regular_file(self):
        path = self.create_file("test-file")
        file = File(path)
        file_group_name = file.group_name()
        self.assertEqual(file_group_name, "user")

    def test_can_get_group_name_of_directory(self):
        path = self.create_directory("test-dir")
        file = File(path)
        file_group_name = file.group_name()
        self.assertEqual(file_group_name, "user")

    def test_getting_group_name_of_nonexistent_file_raises_exception(self):
        file = File(self.create_path("nonexistent-file"))
        with self.assertRaises(FileNotFoundException) as raised:
            file.group_name()

        self.assertIn(
            "Failed to get file group name for file",
            str(raised.exception)
        )
        self.assertIn("File does not exist", str(raised.exception))
        self.assertEqual(raised.exception.file_path, str(file.path))

    def test_can_get_modification_time_of_regular_file(self):
        path = self.create_file("test-file")
        file = File(path)
        file.write_all(b"AAAAAAAA")
        modification_time = file.modification_time()
        self.assertEqual(
            modification_time,
            datetime.datetime(
                year=2022, month=5, day=25,
                hour=14, minute=15, second=16,
                tzinfo=datetime.UTC,
            )
        )

    def test_getting_modification_time_of_nonexistent_file_raises_ex(self):
        file = File(self.create_path("nonexistent-file"))
        with self.assertRaises(FileNotFoundException) as raised:
            file.modification_time()

        self.assertIn(
            "Failed to get last modification time for file",
            str(raised.exception)
        )
        self.assertIn("File does not exist", str(raised.exception))
        self.assertEqual(raised.exception.file_path, str(file.path))

    def test_info_string_format_for_regular_file(self):
        test_data = "A" * int(4.321 * 10**6)  # 4.321MB
        path = self.create_file("test-file", test_data)
        # Owner and group
        og = "user"
        # Modification time
        mt = datetime.datetime(
            year=2022, month=5, day=25,
            hour=14, minute=15, second=16,
            tzinfo=None,
        ).isoformat(timespec="seconds")

        expected_info = f"-rw-rw-r-- {og} {og} 4.32MB {mt} test-file"
        file = File(path)
        info = file.info()
        self.assertEqual(info, expected_info)
        self.assertTrue(File(path).exists())

    def test_info_string_format_for_directory(self):
        test_data = "A" * int(5.33 * 10**3)  # 5.33KB
        path = self.create_directory("test-dir")
        self.create_file(path / "file-A", test_data)
        self.create_file(path / "file-B", test_data)
        self.create_file(path / "file-C", test_data)
        # Owner and group
        og = "user"
        # Modification time
        mt = datetime.datetime(
            year=2022, month=5, day=25,
            hour=14, minute=15, second=16,
            tzinfo=None,
        ).isoformat(timespec="seconds")

        expected_info = f"drwxrwxr-x {og} {og} 15.99KB {mt} test-dir"
        file = File(path)
        actual_info = file.info()
        self.assertEqual(expected_info, actual_info)
        self.assertTrue(File(path).is_directory())

    def test_info_string_format_for_symlink_to_regular_file(self):
        test_data = "A" * int(4.321 * 10**6)  # 4.321MB
        path_file = self.create_file("test-file", test_data)
        path_link = self.create_path("test-link")
        File(path_link).create_symbolic_link(path_file)
        # Owner and group
        og = "user"
        # Modification time
        mt_file = datetime.datetime(
            year=2022, month=5, day=25,
            hour=14, minute=15, second=16,
            tzinfo=None,
        ).isoformat(timespec="seconds")
        mt_link = mt_file

        expected_info = f"-rw-rw-r-- {og} {og} 4.32MB {mt_file} test-file"
        file = File(path_file)
        file.follow_symlinks = True
        actual_info = file.info()
        self.assertEqual(expected_info, actual_info)
        file = File(path_link)
        file.follow_symlinks = False
        fname = f"test-link -> {self.testdir}{self.sep}test-file"
        expected_info = f"lrw-rw-r-- {og} {og} 4.32MB {mt_link} {fname}"
        actual_info = file.info()
        self.assertEqual(expected_info, actual_info)
        file.remove()
        File(path_link).create_symbolic_link("test-file")
        fname = "test-link -> test-file"
        expected_info = f"lrw-rw-r-- {og} {og} 4.32MB {mt_link} {fname}"
        actual_info = file.info()
        self.assertEqual(expected_info, actual_info)

    def test_get_info_string_on_nonexistent_file_returns_empty_string(self):
        nonexistent_file = File(self.create_path("this-file-does-not-exist"))
        info_of_nonexistent_file = nonexistent_file.info()
        self.assertIsInstance(info_of_nonexistent_file, str)
        self.assertEqual(info_of_nonexistent_file, "")

    def test_regular_file_exists(self):
        path = self.create_path("test-file")
        file = File(path)
        self.assertFalse(file.exists())
        self.create_file(path)
        self.assertTrue(file.exists())

    def test_directory_exists(self):
        path = self.create_path("test-dir")
        file = File(path)
        self.assertFalse(file.exists())
        self.create_directory(path)
        self.assertTrue(file.exists())

    def test_symbolic_link_exists(self):
        path_target = self.create_file("test-file-target")
        file = File(self.create_path("test-link"))
        file.create_symbolic_link(path_target)
        self.assertTrue(file.exists())
        File(path_target).remove()
        self.assertFalse(file.exists())
        file.follow_symlinks = False
        self.assertTrue(file.exists())

    def test_can_list_files(self):
        self.create_directory("dir_a/dir_b/dir_c")
        self.create_file("dir_a/dir_b/test-file")
        self.create_directory("dir_a/dir_d")
        self.create_file("dir_a/test-file-1")
        self.create_file("dir_a/test-file-2")
        self.create_file("dir_a/test-file-3")
        test_dir = File(self.create_path("dir_a"))
        found_files = test_dir.list_files()
        self.assertIsInstance(found_files, types.GeneratorType)
        found_files_list = list(found_files)
        self.assertEqual(len(found_files_list), 5)
        self.assertIn(File(self.create_path("dir_a/dir_b")), found_files_list)
        self.assertIn(File(self.create_path("dir_a/dir_d")), found_files_list)
        self.assertIn(
            File(self.create_path("dir_a/test-file-1")),
            found_files_list
        )
        self.assertIn(
            File(self.create_path("dir_a/test-file-2")),
            found_files_list
        )
        self.assertIn(
            File(self.create_path("dir_a/test-file-3")),
            found_files_list
        )

    def test_attempting_to_list_files_on_non_dir_raises_exception(self):
        path = self.create_file("non-directory")
        file = File(path)
        with self.assertRaises(DirectoryListingException) as raised:
            list(file.list_files())

        self.assertIn(
            "Cannot generate directory listing for non-directory file",
            str(raised.exception)
        )
        self.assertEqual(raised.exception.file_path, str(path))

    def test_getting_file_list_for_nonexistent_dir_raises_ex(self):
        file = File(self.create_path("nonexistent-dir"))
        with self.assertRaises(FileNotFoundException) as raised:
            list(file.list_files())

        self.assertIn(
            "Failed to generate listing for directory",
            str(raised.exception)
        )
        self.assertIn("Directory does not exist", str(raised.exception))
        self.assertEqual(raised.exception.file_path, str(file.path))

    def test_can_list_all_files(self):
        self.create_directory("dir_a/dir_b/dir_c")
        self.create_file("dir_a/dir_b/dir_c/test-file-c")
        self.create_file("dir_a/dir_b/test-file-b")
        self.create_directory("dir_a/dir_d")
        self.create_file("dir_a/test-file-1")
        self.create_file("dir_a/test-file-2")
        self.create_file("dir_a/test-file-3")
        test_dir = File(self.create_path("dir_a"))
        found_files = test_dir.list_all_files()
        self.assertIsInstance(found_files, types.GeneratorType)
        found_files_list = list(found_files)
        self.assertEqual(len(found_files_list), 8)
        self.assertIn(
            File(self.create_path("dir_a/dir_b")),
            found_files_list
        )
        self.assertIn(
            File(self.create_path("dir_a/dir_b/test-file-b")),
            found_files_list
        )
        self.assertIn(
            File(self.create_path("dir_a/dir_b/dir_c")),
            found_files_list
        )
        self.assertIn(
            File(self.create_path("dir_a/dir_b/dir_c/test-file-c")),
            found_files_list
        )
        self.assertIn(
            File(self.create_path("dir_a/dir_d")),
            found_files_list
        )
        self.assertIn(
            File(self.create_path("dir_a/test-file-1")),
            found_files_list
        )
        self.assertIn(
            File(self.create_path("dir_a/test-file-2")),
            found_files_list
        )
        self.assertIn(
            File(self.create_path("dir_a/test-file-3")),
            found_files_list
        )

    def test_attempting_to_list_all_files_on_non_dir_raises_exception(self):
        path = self.create_file("non-directory")
        file = File(path)
        with self.assertRaises(DirectoryListingException) as raised:
            list(file.list_all_files())

        self.assertIn(
            "Cannot generate directory listing for non-directory file",
            str(raised.exception)
        )
        self.assertEqual(raised.exception.file_path, str(path))

    def test_getting_file_list_all_for_nonexistent_dir_raises_ex(self):
        file = File(self.create_path("nonexistent-dir"))
        with self.assertRaises(FileNotFoundException) as raised:
            list(file.list_all_files())

        self.assertIn(
            "Failed to generate listing for directory",
            str(raised.exception)
        )
        self.assertIn("Directory does not exist", str(raised.exception))
        self.assertEqual(raised.exception.file_path, str(file.path))

    def test_can_follow_symbolic_link(self):
        path_target = self.create_file("test-file-target")
        path_link_1 = self.create_path("test-link-1")
        path_link_2 = self.create_path("test-link-2")
        path_link_3 = self.create_path("test-link-3")
        file_target = File(path_target)
        file_link_1 = File(path_link_1)
        file_link_2 = File(path_link_2)
        file_link_3 = File(path_link_3)
        file_link_1.create_symbolic_link(file_target)
        file_link_2.create_symbolic_link(file_link_1)
        file_link_3.create_symbolic_link(file_link_2)
        file_resolved_link = file_link_3.resolve_symbolic_links()
        self.assertEqual(file_resolved_link, file_target)

    def test_can_determine_if_file_is_hidden(self):
        file_visible = File(self.create_file("test-file-visible"))
        file_hidden = File(self.create_file(".test-file-hidden"))
        self.assertFalse(file_visible.is_hidden())
        self.assertTrue(file_hidden.is_hidden())

    def test_is_hidden_for_nonexistent_file_raises_exception(self):
        file = File(self.create_path("this-file-does-not-exist"))
        with self.assertRaises(FileNotFoundException) as raised:
            file.is_hidden()

        self.assertIn(
            "Failed to check if file is hidden",
            str(raised.exception)
        )
        self.assertIn("No such file or directory", str(raised.exception))
        self.assertEqual(raised.exception.file_path, str(file.path))

    def test_can_make_regular_file_hidden(self):
        path = self.create_file("test-file")
        file = File(path)
        self.assertFalse(file.is_hidden())
        hidden_file = file.make_hidden()
        self.assertIsInstance(hidden_file, File)
        self.assertEqual(hidden_file.name, ".test-file")
        self.assertTrue(hidden_file.is_hidden())
        self.assertFileDoesNotExist(path)
        self.assertFileExists(hidden_file.path)

    def test_attempting_to_make_open_file_hidden_raises_exception(self):
        path = self.create_file("test-file")
        file = File(path)
        with self.assertRaises(InvalidFileStateException) as raised:
            with file.open(FileMode.READ_WRITE):
                file.make_hidden()

        self.assertIn("Cannot hide file", str(raised.exception))
        self.assertIn(
            "File must not be open when making hidden",
            str(raised.exception)
        )
        self.assertEqual(raised.exception.file_path, str(file.path))

    def test_can_make_directory_hidden(self):
        path = self.create_directory("test-dir")
        file = File(path)
        self.assertFalse(file.is_hidden())
        hidden_dir = file.make_hidden()
        self.assertIsInstance(hidden_dir, File)
        self.assertEqual(hidden_dir.name, ".test-dir")
        self.assertTrue(hidden_dir.is_hidden())
        self.assertFileDoesNotExist(path)
        self.assertFileExists(hidden_dir.path)

    def test_hiding_already_hidden_file_has_no_effect(self):
        path = self.create_file(".test-file")
        file = File(path)
        self.assertTrue(file.is_hidden())
        hidden_file = file.make_hidden()
        self.assertIsInstance(hidden_file, File)
        self.assertEqual(hidden_file.name, ".test-file")
        self.assertTrue(hidden_file.is_hidden())
        self.assertTrue(File(path).exists())
        self.assertFileExists(hidden_file.path)
        self.assertEqual(file, hidden_file)

    def test_hiding_file_copies_properties_to_returned_file(self):
        path = self.create_file("test-file")
        file = File(path)
        file.follow_symlinks = False
        file.text_encoding = "UTF-32"
        file.line_separator = "!"
        hidden_file = file.make_hidden()
        self.assertEqual(hidden_file.follow_symlinks, file.follow_symlinks)
        self.assertEqual(hidden_file.text_encoding, file.text_encoding)
        self.assertEqual(hidden_file.line_separator, file.line_separator)

    def test_can_make_regular_file_visible(self):
        path = self.create_file(".test-file")
        file = File(path)
        self.assertTrue(file.is_hidden())
        visible_file = file.make_visible()
        self.assertIsInstance(visible_file, File)
        self.assertEqual(visible_file.name, "test-file")
        self.assertFalse(visible_file.is_hidden())
        self.assertFileDoesNotExist(path)
        self.assertFileExists(visible_file.path)

    def test_attempting_to_make_open_file_visible_raises_exception(self):
        path = self.create_file("test-file")
        file = File(path)
        with self.assertRaises(InvalidFileStateException) as raised:
            with file.open(FileMode.READ_WRITE):
                file.make_visible()

        self.assertIn("Cannot unhide file", str(raised.exception))
        self.assertIn(
            "File must not be open when making visible",
            str(raised.exception)
        )
        self.assertEqual(raised.exception.file_path, str(file.path))

    def test_can_make_directory_visible(self):
        path = self.create_directory(".test-dir")
        file = File(path)
        self.assertTrue(file.is_hidden())
        visible_dir = file.make_visible()
        self.assertIsInstance(visible_dir, File)
        self.assertEqual(visible_dir.name, "test-dir")
        self.assertFalse(visible_dir.is_hidden())
        self.assertFileDoesNotExist(path)
        self.assertFileExists(visible_dir.path)

    def test_making_visible_already_visible_file_has_no_effect(self):
        path = self.create_file("test-file")
        file = File(path)
        self.assertFalse(file.is_hidden())
        visible_file = file.make_visible()
        self.assertIsInstance(visible_file, File)
        self.assertEqual(visible_file.name, "test-file")
        self.assertFalse(visible_file.is_hidden())
        self.assertTrue(File(path).exists())
        self.assertFileExists(visible_file.path)
        self.assertEqual(file, visible_file)

    def test_attempting_to_make_locked_file_hidden_raises_exception(self):
        path = self.create_file("test-file")
        file = File(path)
        with file.lock():
            with self.assertRaises(InvalidFileStateException) as raised:
                file.make_hidden()

            self.assertIn("Cannot hide file", str(raised.exception))
            self.assertIn(
                "File must not be locked when making hidden",
                str(raised.exception)
            )
            self.assertEqual(raised.exception.file_path, str(file.path))

    def test_attempting_to_make_locked_file_visible_raises_exception(self):
        path = self.create_file(".test-file")
        file = File(path)
        with file.lock():
            with self.assertRaises(InvalidFileStateException) as raised:
                file.make_visible()

            self.assertIn("Cannot unhide file", str(raised.exception))
            self.assertIn(
                "File must not be locked when making visible",
                str(raised.exception)
            )
            self.assertEqual(raised.exception.file_path, str(file.path))

    def test_making_file_visible_copies_properties_to_returned_file(self):
        path = self.create_file(".test-file")
        file = File(path)
        file.follow_symlinks = False
        file.text_encoding = "UTF-32"
        file.line_separator = "!"
        visible_file = file.make_visible()
        self.assertEqual(visible_file.follow_symlinks, file.follow_symlinks)
        self.assertEqual(visible_file.text_encoding, file.text_encoding)
        self.assertEqual(visible_file.line_separator, file.line_separator)

    def test_can_get_single_suffix_from_file(self):
        file = File(self.create_file("test-file.txt"))
        self.assertEqual(file.get_suffix(), ".txt")

    def test_can_get_composite_suffix_from_file(self):
        file = File(self.create_file("test-archive.x.tar.gz"))
        self.assertEqual(file.get_suffix(), ".x.tar.gz")

    def test_can_add_suffix_to_file_name(self):
        file = File(self.create_file("test-file"))
        file_with_suffix = file.with_suffix(".txt")
        self.assertIsInstance(file_with_suffix, File)
        self.assertEqual(file.name, "test-file")
        self.assertEqual(file_with_suffix.name, "test-file.txt")
        self.assertFileExists(file.path)
        self.assertFileDoesNotExist(file_with_suffix.path)

    def test_adding_suffix_to_file_with_same_suffix_returns_same_obj(self):
        file = File(self.create_file("test-file.py"))
        file_with_suffix = file.with_suffix(".py")
        self.assertIsInstance(file_with_suffix, File)
        self.assertIs(file, file_with_suffix)

    def test_replace_suffix_to_file_with_other_suffix(self):
        file = File(self.create_file("test-file.data.txt"))
        file_with_suffix = file.with_suffix(".gz")
        self.assertIsInstance(file_with_suffix, File)
        self.assertEqual(file.name, "test-file.data.txt")
        self.assertEqual(file_with_suffix.name, "test-file.data.gz")
        self.assertFileExists(file.path)
        self.assertFileDoesNotExist(file_with_suffix.path)

    def test_add_suffix_to_file_with_other_suffix(self):
        file = File(self.create_file("test-file.data.txt"))
        file_with_suffix = file.append_suffix(".gz")
        self.assertIsInstance(file_with_suffix, File)
        self.assertEqual(file.name, "test-file.data.txt")
        self.assertEqual(file_with_suffix.name, "test-file.data.txt.gz")
        self.assertFileExists(file.path)
        self.assertFileDoesNotExist(file_with_suffix.path)

    def test_can_remove_single_file_name_suffix(self):
        file = File(self.create_file("test-file.data.txt"))
        file_without_suffix = file.without_suffix(".txt")
        self.assertIsInstance(file_without_suffix, File)
        self.assertEqual(file.name, "test-file.data.txt")
        self.assertEqual(file_without_suffix.name, "test-file.data")
        self.assertFileExists(file.path)
        self.assertFileDoesNotExist(file_without_suffix.path)

    def test_can_remove_composite_file_name_suffix(self):
        file = File(self.create_file("test-file.data.txt"))
        file_without_suffix = file.without_suffix(".data.txt")
        self.assertIsInstance(file_without_suffix, File)
        self.assertEqual(file.name, "test-file.data.txt")
        self.assertEqual(file_without_suffix.name, "test-file")
        self.assertFileExists(file.path)
        self.assertFileDoesNotExist(file_without_suffix.path)

    def test_can_remove_file_name_suffix_without_dot_notation(self):
        file = File(self.create_file("test-file.data.txt"))
        file_without_suffix = file.without_suffix("txt")
        self.assertIsInstance(file_without_suffix, File)
        self.assertEqual(file.name, "test-file.data.txt")
        self.assertEqual(file_without_suffix.name, "test-file.data")
        self.assertFileExists(file.path)
        self.assertFileDoesNotExist(file_without_suffix.path)

    def test_can_remove_suffix_when_not_specifying_suffix_explicitly(self):
        file = File(self.create_file("test-file.data.txt"))
        file_without_suffix = file.without_suffix()
        self.assertIsInstance(file_without_suffix, File)
        self.assertEqual(file.name, "test-file.data.txt")
        self.assertEqual(file_without_suffix.name, "test-file")
        self.assertFileExists(file.path)
        self.assertFileDoesNotExist(file_without_suffix.path)

    def test_can_read_all_bytes(self):
        test_data = b"TEST_DATA_FILE_CONTENT"
        file = File(self.create_file("test-file", test_data))
        self.assertFalse(file.is_open())
        file_data = file.read_all_bytes()
        self.assertIsInstance(file_data, bytes)
        self.assertEqual(file_data, test_data)
        self.assertFalse(file.is_open())

    def test_can_read_all_bytes_when_file_is_already_open(self):
        test_data = b"TEST_DATA_FILE_CONTENT"
        file = File(self.create_file("test-file", test_data))
        file.open(FileMode.READ_WRITE)
        self.assertTrue(file.is_open())
        file_data = file.read_all_bytes()
        self.assertIsInstance(file_data, bytes)
        self.assertEqual(file_data, test_data)
        self.assertTrue(file.is_open())

    def test_reading_all_bytes_from_open_file_with_wrong_mode_raises_ex(self):
        test_data = b"TEST_DATA_FILE_CONTENT"
        file = File(self.create_file("test-file", test_data))
        file.open(FileMode.WRITE)
        self.assertTrue(file.is_open())
        with self.assertRaises(InvalidFileModeException) as raised:
            file.read_all_bytes()

        self.assertIn(
            "Cannot read all bytes from file", str(raised.exception)
        )
        self.assertIn(
            "File is already open in WRITE mode which does not allow reading",
            str(raised.exception)
        )
        self.assertEqual(raised.exception.file_path, str(file.path))
        self.assertTrue(file.is_open())

    def test_can_read_all_text(self):
        test_data = "TEST_DATA_FILE_CONTENT"
        file = File(self.create_file("test-file", test_data))
        self.assertFalse(file.is_open())
        file_data = file.read_all_text()
        self.assertIsInstance(file_data, str)
        self.assertEqual(file_data, test_data)
        self.assertFalse(file.is_open())

    def test_can_read_all_text_with_custom_encoding(self):
        test_data = "TEST_DATA_FILE_CONTENT"
        test_encoding = "UTF-16LE"
        file = File(self.create_file("test-file", test_data, test_encoding))
        file.text_encoding = test_encoding
        self.assertFalse(file.is_open())
        file_data = file.read_all_text()
        self.assertIsInstance(file_data, str)
        self.assertEqual(file_data, test_data)
        self.assertFalse(file.is_open())

    def test_reading_all_text_with_invalid_encoding_raises_exception(self):
        test_data = "TEST_DATA_FILE_CONTENT"
        file = File(self.create_file("test-file", test_data))
        file.text_encoding = "AN-INVALID-ENCODING"
        with self.assertRaises(FileTextDecodeException) as raised:
            file.read_all_text()

        self.assertIn(
            "Invalid encoding",
            str(raised.exception)
        )
        self.assertEqual(raised.exception.file_path, str(file.path))

    def test_reading_text_with_wrongly_encoded_text_raises_exception(self):
        test_data = b"TEST_DATA_\xf0\x0f\x9f\x99\x83_WITH_INVALID_BYTES"
        file = File(self.create_file("test-file", test_data))
        with self.assertRaises(FileTextDecodeException) as raised:
            file.read_all_text()

        self.assertIn(
            "Failed to decode UTF-8 text while reading file",
            str(raised.exception)
        )
        self.assertEqual(raised.exception.file_path, str(file.path))

    def test_can_read_all_text_when_file_is_already_open(self):
        test_data = "TEST_DATA_FILE_CONTENT"
        file = File(self.create_file("test-file", test_data))
        file.open(FileMode.READ_WRITE)
        self.assertTrue(file.is_open())
        file_data = file.read_all_text()
        self.assertIsInstance(file_data, str)
        self.assertEqual(file_data, test_data)
        self.assertTrue(file.is_open())

    def test_can_read_all_text_lines(self):
        test_data = "line-a\nline-b\n\n\nline-c\nline-d\n"
        file = File(self.create_file("test-file", test_data))
        self.assertFalse(file.is_open())
        lines = file.read_all_text_lines()
        self.assertIsInstance(lines, list)
        self.assertFalse(file.is_open())
        self.assertEqual(len(lines), 6)
        self.assertEqual(lines[0], "line-a")
        self.assertEqual(lines[1], "line-b")
        self.assertEqual(lines[2], "")
        self.assertEqual(lines[3], "")
        self.assertEqual(lines[4], "line-c")
        self.assertEqual(lines[5], "line-d")
        self.assertFalse(file.is_open())

    def test_can_read_all_text_lines_excluding_empty_lines(self):
        test_data = "\n\nline-a\nline-b\n\n\nline-c\nline-d\n\n"
        file = File(self.create_file("test-file", test_data))
        lines = file.read_all_text_lines(include_empty=False)
        self.assertIsInstance(lines, list)
        self.assertFalse(file.is_open())
        self.assertEqual(len(lines), 4)
        self.assertEqual(lines[0], "line-a")
        self.assertEqual(lines[1], "line-b")
        self.assertEqual(lines[2], "line-c")
        self.assertEqual(lines[3], "line-d")

    def test_can_read_all_text_lines_with_custom_encoding(self):
        test_data = "\n\nline-a\nline-b\n\n\nline-c\nline-d\n\n"
        test_encoding = "UTF-16LE"
        file = File(self.create_file("test-file", test_data, test_encoding))
        file.text_encoding = test_encoding
        lines = file.read_all_text_lines(include_empty=False)
        self.assertIsInstance(lines, list)
        self.assertFalse(file.is_open())
        self.assertEqual(len(lines), 4)
        self.assertEqual(lines[0], "line-a")
        self.assertEqual(lines[1], "line-b")
        self.assertEqual(lines[2], "line-c")
        self.assertEqual(lines[3], "line-d")

    def test_can_read_all_text_lines_when_file_is_already_open(self):
        test_data = "line-a\nline-b\n\n\nline-c\nline-d\n"
        file = File(self.create_file("test-file", test_data))
        file.open(FileMode.READ)
        self.assertTrue(file.is_open())
        lines = file.read_all_text_lines()
        self.assertIsInstance(lines, list)
        self.assertEqual(len(lines), 6)
        self.assertTrue(file.is_open())

    def test_can_write_all_bytes_to_file(self):
        test_data = b"TEST_DATA_FILE_CONTENT"
        path = self.create_path("test-file")
        file = File(path)
        self.assertFalse(file.is_open())
        n_bytes_written = file.write_all(test_data)
        self.assertIsInstance(n_bytes_written, int)
        self.assertFalse(file.is_open())
        self.assertEqual(n_bytes_written, len(test_data))
        self.assertFileContent(path, test_data)

    def test_can_write_all_bytes_to_file_when_file_is_already_open(self):
        test_data = b"TEST_DATA_FILE_CONTENT"
        path = self.create_path("test-file")
        file = File(path)
        file.open(FileMode.WRITE)
        self.assertTrue(file.is_open())
        n_bytes_written = file.write_all(test_data)
        self.assertIsInstance(n_bytes_written, int)
        self.assertFileContent(path, test_data)
        self.assertTrue(file.is_open())

    def test_can_write_all_bytes_from_bytearray_to_file(self):
        test_data = bytearray(b"TEST_DATA_FILE_CONTENT")
        path = self.create_path("test-file")
        file = File(path)
        self.assertFalse(file.is_open())
        n_bytes_written = file.write_all(test_data)
        self.assertIsInstance(n_bytes_written, int)
        self.assertFalse(file.is_open())
        self.assertEqual(n_bytes_written, len(test_data))
        self.assertFileContent(path, test_data)

    def test_can_write_all_text_to_file(self):
        test_data = "TEST_DATA_FILE_CONTENT"
        path = self.create_path("test-file")
        file = File(path)
        self.assertFalse(file.is_open())
        n_bytes_written = file.write_all(test_data)
        self.assertIsInstance(n_bytes_written, int)
        self.assertFalse(file.is_open())
        self.assertEqual(n_bytes_written, len(test_data))
        self.assertFileContent(path, test_data)

    def test_can_write_all_text_to_file_when_file_is_already_open(self):
        test_data = "TEST_DATA_FILE_CONTENT"
        path = self.create_path("test-file")
        file = File(path)
        file.open(FileMode.WRITE)
        self.assertTrue(file.is_open())
        n_bytes_written = file.write_all(test_data)
        self.assertIsInstance(n_bytes_written, int)
        self.assertFileContent(path, test_data)
        self.assertTrue(file.is_open())

    def test_can_write_all_text_with_custom_encoding(self):
        test_data = "TEST_DATA_FILE_CONTENT"
        test_encoding = "UTF-16LE"
        path = self.create_path("test-file")
        file = File(path)
        self.assertFalse(file.is_open())
        file.text_encoding = test_encoding
        n_bytes_written = file.write_all(test_data)
        self.assertIsInstance(n_bytes_written, int)
        self.assertFalse(file.is_open())
        self.assertEqual(n_bytes_written, len(test_data.encode(test_encoding)))
        self.assertFileContent(path, test_data.encode(test_encoding))

    def test_can_write_all_bytes_to_already_open_file(self):
        test_data = b"TEST_DATA_FILE_CONTENT"
        path = self.create_path("test-file")
        file = File(path)
        file.open(FileMode.CREATE_READ_WRITE)
        self.assertTrue(file.is_open())
        n_bytes_written = file.write_all(test_data)
        self.assertIsInstance(n_bytes_written, int)
        self.assertTrue(file.is_open())
        self.assertEqual(n_bytes_written, len(test_data))
        self.assertFileContent(path, test_data)

    def test_can_write_all_bytes_to_existent_file(self):
        test_data = b"TEST_DATA_FILE_CONTENT"
        path = self.create_file("test-file", b"other_data_content")
        file = File(path)
        self.assertFalse(file.is_open())
        n_bytes_written = file.write_all(test_data)
        self.assertIsInstance(n_bytes_written, int)
        self.assertFalse(file.is_open())
        self.assertEqual(n_bytes_written, len(test_data))
        self.assertFileContent(path, test_data)

    def test_writing_all_text_with_invalid_encoding_to_file_raises_ex(self):
        test_data = "TEST_DATA_FILE_CONTENT"
        file = File(self.create_path("test-file"))
        file.text_encoding = "AN-INVALID-ENCODING"
        with self.assertRaises(FileTextEncodeException) as raised:
            file.write_all(test_data)

        self.assertIn(
            "Failed to encode text while trying to write to file",
            str(raised.exception)
        )
        self.assertIn(
            f"Invalid encoding '{file.text_encoding}'",
            str(raised.exception)
        )
        self.assertEqual(raised.exception.file_path, str(file.path))

    def test_can_append_all_bytes_to_file(self):
        test_data = b"TEST_DATA_FILE_CONTENT"
        original_data = b"other_data_content"
        path = self.create_file("test-file", original_data)
        file = File(path)
        self.assertFalse(file.is_open())
        n_bytes_written = file.append_all(test_data)
        self.assertIsInstance(n_bytes_written, int)
        self.assertFalse(file.is_open())
        self.assertEqual(n_bytes_written, len(test_data))
        self.assertFileContent(path, original_data + test_data)

    def test_can_append_all_bytes_from_bytearray_to_file(self):
        test_data = bytearray(b"TEST_DATA_FILE_CONTENT")
        original_data = bytearray(b"other_data_content")
        path = self.create_file("test-file", original_data)
        file = File(path)
        self.assertFalse(file.is_open())
        n_bytes_written = file.append_all(test_data)
        self.assertIsInstance(n_bytes_written, int)
        self.assertFalse(file.is_open())
        self.assertEqual(n_bytes_written, len(test_data))
        self.assertFileContent(path, original_data + test_data)

    def test_can_append_all_text_to_file(self):
        test_data = "TEST_DATA_FILE_CONTENT"
        original_data = "other_data_content+"
        path = self.create_file("test-file", original_data)
        file = File(path)
        self.assertFalse(file.is_open())
        n_bytes_written = file.append_all(test_data)
        self.assertIsInstance(n_bytes_written, int)
        self.assertFalse(file.is_open())
        self.assertEqual(n_bytes_written, len(test_data))
        self.assertFileContent(path, original_data + test_data)

    def test_can_append_all_text_with_custom_encoding(self):
        test_data = "TEST_DATA_FILE_CONTENT"
        test_encoding = "UTF-16LE"
        original_data = "other_data_content"
        path = self.create_file("test-file", original_data)
        file = File(path)
        self.assertFalse(file.is_open())
        file.text_encoding = test_encoding
        n_bytes_written = file.append_all(test_data)
        self.assertIsInstance(n_bytes_written, int)
        self.assertFalse(file.is_open())
        self.assertEqual(n_bytes_written, len(test_data.encode(test_encoding)))
        self.assertFileContent(
            path,
            original_data.encode() + test_data.encode(test_encoding)
        )

    def test_can_append_all_bytes_to_already_open_file(self):
        test_data = b"TEST_DATA_FILE_CONTENT"
        original_data = b"other_data_content"
        path = self.create_file("test-file", original_data)
        file = File(path)
        file.open(FileMode.READ_APPEND)
        self.assertTrue(file.is_open())
        n_bytes_written = file.append_all(test_data)
        self.assertIsInstance(n_bytes_written, int)
        self.assertTrue(file.is_open())
        self.assertEqual(n_bytes_written, len(test_data))
        self.assertFileContent(path, original_data + test_data)

    def test_can_append_all_bytes_to_existent_file(self):
        test_data = b"TEST_DATA_FILE_CONTENT"
        original_data = b"other_data_content"
        path = self.create_file(
            "test-file", original_data
        )
        file = File(path)
        self.assertFalse(file.is_open())
        n_bytes_written = file.append_all(test_data)
        self.assertIsInstance(n_bytes_written, int)
        self.assertFalse(file.is_open())
        self.assertEqual(n_bytes_written, len(test_data))
        self.assertFileContent(path, original_data + test_data)

    def test_append_all_text_with_invalid_encoding_to_file_raises_ex(self):
        test_data = "TEST_DATA_FILE_CONTENT"
        path = self.create_file("test-file", b"other_data_content")
        file = File(path)
        file.text_encoding = "AN-INVALID-ENCODING"
        with self.assertRaises(FileTextEncodeException) as raised:
            file.append_all(test_data)

        self.assertIn(
            "Failed to encode text while trying to write to file",
            str(raised.exception)
        )
        self.assertIn(
            f"Invalid encoding '{file.text_encoding}'",
            str(raised.exception)
        )
        self.assertEqual(raised.exception.file_path, str(file.path))

    def test_equal_operator_with_str_path(self):
        file = File(self.create_path("test-file"))
        string_path = self.create_path_str("test-file")
        self.assertTrue(file == string_path)

    def test_equal_operator_with_path_obj(self):
        file = File(self.create_path_str("test-file"))
        path_obj = self.create_path("test-file")
        self.assertTrue(file == path_obj)

    def test_equal_operator_with_file_arg(self):
        file_1 = File(self.create_path("test-file"))
        file_2 = File(self.create_path("test-file"))
        self.assertTrue(file_1 == file_2)

    def test_equal_operator_with_wrong_argument_type_raises_exception(self):
        file = File(self.create_path("test-file"))
        with self.assertRaises(TypeError) as raised:
            # pylint: disable=W0104
            file == b"test-file" # type: ignore

        self.assertIn(
            "Cannot compare File instance with object of type",
            str(raised.exception)
        )

    def test_not_equal_operator_with_str_path(self):
        file = File(self.create_path("test-file"))
        string_path = self.create_path_str(".test-file")
        self.assertTrue(file != string_path)

    def test_not_equal_operator_with_path_obj(self):
        file = File(self.create_path_str("test-file"))
        path_obj = self.create_path("test-file2")
        self.assertTrue(file != path_obj)

    def test_not_equal_operator_with_file_arg(self):
        file_1 = File(self.create_path("test-file"))  # Absolute
        file_2 = File("test-file")  # Relative
        self.assertTrue(file_1 != file_2)

    def test_not_equal_operator_with_wrong_argument_type_raises_ex(self):
        file = File(self.create_path("test-file"))
        with self.assertRaises(TypeError) as raised:
            # pylint: disable=W0104
            file != b"test-file" # type: ignore

        self.assertIn(
            "Cannot compare File instance with object of type",
            str(raised.exception)
        )

    def test_hash_value_for_equal_file_is_the_same(self):
        file_1 = File(self.create_path("test-file"))
        file_2 = File(self.create_path("test-file"))
        self.assertEqual(hash(file_1), hash(file_2))

    def test_hash_value_for_identical_file_is_the_same(self):
        file = File(self.create_path("test-file"))
        self.assertEqual(hash(file), hash(file))

    def test_div_operator_with_str_path(self):
        test_dir = File(self.create_path("test-dir"))
        combined_file = test_dir / "test-file"
        self.assertEqual(
            combined_file,
            File(self.create_path("test-dir/test-file"))
        )

    def test_div_operator_with_path_obj(self):
        test_dir = File(self.create_path("test-dir"))
        test_file = File("test-file").path
        combined_file = test_dir / test_file

        self.assertEqual(
            combined_file,
            File(self.create_path("test-dir/test-file"))
        )

    def test_div_operator_with_file_arg(self):
        test_dir = File(self.create_path("test-dir"))
        test_file = File("test-file")
        combined_file = test_dir / test_file

        self.assertEqual(
            combined_file,
            File(self.create_path("test-dir/test-file"))
        )

    def test_context_manager(self):
        path = self.create_path("test-file")
        file = File(path)
        self.assertFalse(file.is_open())
        with file:
            self.assertFalse(
                file.is_open(),
                "File context manager should not automatically open file"
            )

        self.assertFalse(file.is_open())

    def test_open_and_read_and_auto_close_with_context_manager(self):
        test_data = b"TEST_DATA_FILE_CONTENT"
        file = File(self.create_file("test-file", test_data))
        self.assertFalse(file.is_open())
        with file.open() as ctx_file_obj:
            self.assertIs(file, ctx_file_obj)
            self.assertTrue(file.is_open())
            read_data = file.read()
            self.assertEqual(read_data, test_data)

        self.assertFalse(file.is_open())

    def test_string_representation_relative_path(self):
        path_string = str(PurePath("user/test-file"))
        file = File(path_string)
        self.assertEqual(str(file), path_string)

    def test_string_representation_absolute_path(self):
        path_string = "/home/user/test-file"
        expected_file_path = (
            f"{self.drive}{self.sep}home{self.sep}user{self.sep}test-file"
        )
        path_obj = str(PurePath(path_string))
        file = File(path_obj)
        self.assertEqual(str(file), expected_file_path)

    def test_deleting_file_object_closes_open_file(self):
        path = self.create_file("test-file")
        file = File(path)
        self.assertFalse(file.is_open())
        file.open()
        self.assertTrue(file.is_open())
        # pylint: disable=C2801
        file.__del__()
        self.assertFalse(file.is_open())

    def test_is_locked_returns_false_before_any_lock_operation(self):
        file = File(self.create_path("test-file"))
        self.assertIsInstance(file.is_locked(), bool)
        self.assertFalse(file.is_locked())

    def test_is_locked_returns_true_after_lock_and_false_after_unlock(self):
        path = self.create_file("test-file")
        file = File(path)
        self.assertFalse(file.is_locked())
        file.lock()
        self.assertTrue(file.is_locked())
        file.unlock()
        self.assertFalse(file.is_locked())

    def test_can_lock_regular_file(self):
        path = self.create_file("test-file")
        file = File(path)
        lock_path = File.get_file_system().get_lock_file_path(path)
        self.assertFileDoesNotExist(lock_path)
        self.assertFalse(file.is_locked())
        lock_ret = file.lock()
        self.assertIs(file, lock_ret)
        self.assertTrue(file.is_locked())
        self.assertFileExists(lock_path)
        unlock_ret = file.unlock()
        self.assertIs(file, unlock_ret)
        self.assertFalse(file.is_locked())
        self.assertFileDoesNotExist(lock_path)

    def test_can_lock_directory(self):
        path = self.create_directory("test-dir")
        file = File(path)
        lock_path = File.get_file_system().get_lock_file_path(path)
        self.assertFileDoesNotExist(lock_path)
        self.assertFalse(file.is_locked())
        lock_ret = file.lock()
        self.assertIs(file, lock_ret)
        self.assertTrue(file.is_locked())
        self.assertFileExists(lock_path)
        unlock_ret = file.unlock()
        self.assertIs(file, unlock_ret)
        self.assertFalse(file.is_locked())
        self.assertFileDoesNotExist(lock_path)

    def test_cannot_acquire_lock_for_already_locked_file(self):
        path = self.create_file("test-file")
        file = File(path)
        lock_path = File.get_file_system().get_lock_file_path(path)
        self.assertFileDoesNotExist(lock_path)
        self.assertFalse(file.is_locked())
        file.lock()
        self.assertIs(
            file.lock(),
            file,
            "Should be reentrant lock for same File instance"
        )
        with self.assertRaises(FileLockAcquisitionException) as raised:
            File(file.path).lock()

        self.assertIn("File is already locked", str(raised.exception))
        self.assertEqual(raised.exception.file_path, str(path))
        self.assertFileExists(lock_path)
        self.assertTrue(file.is_locked())

    def test_can_lock_file_with_context_manager(self):
        path = self.create_file("test-file")
        file = File(path)
        lock_path = File.get_file_system().get_lock_file_path(path)
        self.assertFileDoesNotExist(lock_path)
        self.assertFalse(file.is_locked())
        with file.lock() as ctx:
            self.assertIs(ctx, file)
            self.assertTrue(file.is_locked())
            self.assertFileExists(lock_path)

        self.assertFalse(file.is_locked())
        self.assertFileDoesNotExist(lock_path)

    def test_can_lock_and_open_file_with_context_manager(self):
        test_data = b"TEST_DATA_FILE_CONTENT"
        path = self.create_file("test-file", test_data)
        file = File(path)
        lock_path = File.get_file_system().get_lock_file_path(path)
        self.assertFileDoesNotExist(lock_path)
        self.assertFalse(file.is_open())
        self.assertFalse(file.is_locked())
        with file.lock().open(FileMode.READ) as ctx:
            self.assertIs(ctx, file)
            self.assertTrue(file.is_open())
            self.assertTrue(file.is_locked())
            self.assertFileExists(lock_path)
            read_data = file.read()

        self.assertFalse(file.is_open())
        self.assertFalse(file.is_locked())
        self.assertFileDoesNotExist(lock_path)
        self.assertEqual(read_data, test_data)

    def test_attempting_to_lock_already_open_file_raises_exception(self):
        path = self.create_file("test-file")
        file = File(path)
        lock_path = File.get_file_system().get_lock_file_path(path)
        with file.open():
            with self.assertRaises(InvalidFileStateException) as raised:
                file.lock()

        self.assertIn(
            "Attempt to lock already open file",
            str(raised.exception)
        )
        self.assertIn(
            "Files must first be locked and then opened",
            str(raised.exception)
        )
        self.assertEqual(raised.exception.file_path, str(file.path))
        self.assertFalse(file.is_open())
        self.assertFalse(file.is_locked())
        self.assertFileDoesNotExist(lock_path)

    def test_attempting_to_unlock_open_file_produces_warning(self):
        path = self.create_file("test-file")
        file = File(path)
        lock_path = File.get_file_system().get_lock_file_path(path)
        file.lock()
        file.open()
        with warnings.catch_warnings(record=True) as warns:
            file.unlock()

        self.assertFileDoesNotExist(lock_path)
        self.assertEqual(len(warns), 1)
        catched_warning = warns[-1]
        self.assertTrue(issubclass(catched_warning.category, UserWarning))
        self.assertIn(
            "Attempt to release lock on file",
            str(catched_warning.message)
        )
        self.assertIn("which is still open.", str(catched_warning.message))
        self.assertIn(
            "Files should first be closed and then unlocked.",
            str(catched_warning.message)
        )
        file.close()

    def test_ctx_mngr_with_lock_and_open_auto_unlocks_when_open_fails(self):
        path = self.create_path("this-file-does-not-exist")
        file = File(path)
        lock_path = File.get_file_system().get_lock_file_path(path)
        with self.assertRaises(FileNotFoundException):
            # File does not exist, so calling open() with below mode
            # will raise a FileNotFoundException
            with file.lock().open(FileMode.READ_WRITE):
                pass

        self.assertFalse(file.is_open())
        self.assertFalse(file.is_locked())
        self.assertFileDoesNotExist(lock_path)

    def test_lock_file_is_created_for_target_of_symlink(self):
        path = self.create_file("test-file")
        file = File(path)
        link_file = File(self.create_path("test-link"))
        link_file.create_symbolic_link(file)
        lock_path = File.get_file_system().get_lock_file_path(path)
        lock_ret = link_file.lock()
        self.assertIs(link_file, lock_ret)
        self.assertFalse(file.is_locked())
        self.assertTrue(link_file.is_locked())
        self.assertFileExists(lock_path)
        unlock_ret = link_file.unlock()
        self.assertIs(link_file, unlock_ret)
        self.assertFalse(file.is_locked())
        self.assertFalse(link_file.is_locked())
        self.assertFileDoesNotExist(lock_path)

    def test_lock_file_can_be_created_for_symlink(self):
        file = File(self.create_file("test-file"))
        path = self.create_path("test-link")
        link_file = File(path)
        link_file.create_symbolic_link(file)
        link_file.follow_symlinks = False
        lock_path = File.get_file_system().get_lock_file_path(
            path, follow_symlinks=False
        )
        link_file.lock()
        self.assertFalse(file.is_locked())
        self.assertTrue(link_file.is_locked())
        self.assertFileExists(lock_path)
        link_file.unlock()
        self.assertFalse(file.is_locked())
        self.assertFalse(link_file.is_locked())
        self.assertFileDoesNotExist(lock_path)

    def test_locking_file_with_nonexistent_parent_dir_raises_ex(self):
        file = File(self.create_path("dir_a/dir_b/file"))
        with self.assertRaises(FileNotFoundException) as raised:
            file.lock()

        self.assertIn("Failed to acquire lock for file", str(raised.exception))
        self.assertIn(
            "It is required that the parent directory of the file exists "
            "and is writable in order to acquire a lock",
            str(raised.exception)
        )
        self.assertIn("Parent directory does not exist", str(raised.exception))
        self.assertEqual(raised.exception.file_path, str(file.path))

    def test_locking_file_with_nonwritable_parent_dir_raises_ex(self):
        parent_dir = self.create_directory("test-dir")
        File(parent_dir).set_permission(
            FilePermission.of(
                owner=FileAccess.of(readable=True, executable=True),
                group=FileAccess.of(readable=True),
                other=FileAccess.of(readable=True)
            )
        )
        file = File(self.create_path("test-dir/test-file"))
        with self.assertRaises(FilePermissionException) as raised:
            file.lock()

        self.assertIn("Failed to acquire lock for file", str(raised.exception))
        self.assertIn(
            "It is required that the parent directory of the file exists "
            "and is writable in order to acquire a lock",
            str(raised.exception)
        )
        self.assertIn("Permission denied", str(raised.exception))
        self.assertEqual(raised.exception.file_path, str(file.path))

    def test_can_create_specific_temporary_file(self):
        path = self.create_path("temp-test-file")
        file = TemporaryFile(path, auto_remove=False)
        self.assertEqual(file.path, path)
        self.assertFalse(file.exists())
        file.create()
        self.assertTrue(file.exists())
        file.__del__()
        del file
        self.assertTrue(File(path).exists())

    def test_can_create_specific_temporary_file_with_auto_remove(self):
        path = self.create_path("temp-test-file")
        file = TemporaryFile(path, auto_remove=True)
        self.assertEqual(file.path, path)
        self.assertFalse(file.exists())
        file.create()
        self.assertTrue(file.exists())
        file.__del__()
        del file
        self.assertFileDoesNotExist(path)

    def test_can_create_temporary_file_in_specified_directory_as_str(self):
        path = self.create_directory("temp-test-dir")
        path = self.create_path_str("temp-test-dir")
        file = TemporaryFile.create_temporary_file(path)
        file_path = file.path
        self.assertTrue(file.exists())
        self.assertEqual(File(file.path).size().in_bytes(), 0)
        self.assertTrue(file.path.as_posix().startswith(path))
        file.__del__()
        del file
        self.assertFileExists(file_path)

    def test_can_create_temporary_file_in_specified_directory_as_path(self):
        path = self.create_directory("temp-test-dir")
        file = TemporaryFile.create_temporary_file(path)
        file_path = file.path
        self.assertTrue(file.exists())
        self.assertEqual(File(file.path).size().in_bytes(), 0)
        self.assertTrue(str(file.path).startswith(str(path)))
        file.__del__()
        del file
        self.assertFileExists(file_path)

    def test_can_create_temporary_file_in_specified_directory(self):
        path = self.create_directory("temp-test-dir")
        temp_dir = File(path)
        file = TemporaryFile.create_temporary_file(in_directory=temp_dir)
        file_path = file.path
        self.assertTrue(file.exists())
        self.assertEqual(File(file.path).size().in_bytes(), 0)
        self.assertTrue(str(file.path).startswith(str(temp_dir.path)))
        file.__del__()
        del file
        self.assertFileExists(file_path)

    def test_creating_temporary_file_in_nonexistent_dir_raises_ex(self):
        nonexistent_dir = File(self.create_path("this-dir-does-not-exist"))
        with self.assertRaises(FileNotFoundException) as raised:
            TemporaryFile.create_temporary_file(in_directory=nonexistent_dir)

        self.assertIn("Failed to create temporary file", str(raised.exception))
        self.assertIn(
            "because the specified parent directory",
            str(raised.exception)
        )
        self.assertIn("does not exist", str(raised.exception))
        self.assertEqual(raised.exception.file_path, str(nonexistent_dir))
        self.assertFileDoesNotExist(nonexistent_dir.path)

    def test_creating_temporary_file_with_parent_of_wrong_type_raises_ex(self):
        path = self.create_file("a-regular-file")
        file = File(path)
        with self.assertRaises(TemporaryFileCreationException) as raised:
            TemporaryFile.create_temporary_file(in_directory=file)

        self.assertIn("Failed to create temporary file", str(raised.exception))
        self.assertIsNone(raised.exception.file_path)
        self.assertTrue(File(path).exists())

    def test_can_create_temporary_file_with_prefix(self):
        path = self.create_directory("temp-test-dir")
        temp_dir = File(path)
        file = TemporaryFile.create_temporary_file(
            temp_dir,
            prefix="the-test-prefix-"
        )
        file_path = file.path
        self.assertTrue(file.exists())
        self.assertEqual(File(file.path).size().in_bytes(), 0)
        self.assertTrue(str(file.path).startswith(str(temp_dir.path)))
        self.assertTrue(file.name.startswith("the-test-prefix-"))
        self.assertFalse(file.name.endswith("the-test-prefix-"))
        file.__del__()
        del file
        self.assertFileExists(file_path)

    def test_can_create_temporary_file_with_suffix(self):
        path = self.create_directory("temp-test-dir")
        temp_dir = File(path)
        file = TemporaryFile.create_temporary_file(
            temp_dir,
            suffix="-the-test-suffix"
        )
        file_path = file.path
        self.assertTrue(file.exists())
        self.assertEqual(File(file.path).size().in_bytes(), 0)
        self.assertTrue(str(file.path).startswith(str(temp_dir.path)))
        self.assertFalse(file.name.startswith("-the-test-suffix"))
        self.assertTrue(file.name.endswith("-the-test-suffix"))
        file.__del__()
        del file
        self.assertFileExists(file_path)

    def test_can_create_temporary_file_with_prefix_and_suffix(self):
        path = self.create_directory("temp-test-dir")
        temp_dir = File(path)
        file = TemporaryFile.create_temporary_file(
            temp_dir,
            prefix="the-test-prefix-",
            suffix="-the-test-suffix"
        )
        file_path = file.path
        self.assertTrue(file.exists())
        self.assertEqual(File(file.path).size().in_bytes(), 0)
        self.assertTrue(str(file.path).startswith(str(temp_dir.path)))
        self.assertTrue(file.name.startswith("the-test-prefix-"))
        self.assertTrue(file.name.endswith("-the-test-suffix"))
        file.__del__()
        del file
        self.assertFileExists(file_path)

    def test_can_create_temporary_file_with_auto_remove_enabled(self):
        path = self.create_directory("temp-test-dir")
        temp_dir = File(path)
        file = TemporaryFile.create_temporary_file(
            temp_dir,
            prefix="the-test-prefix-",
            suffix="-the-test-suffix"
        )
        file.auto_remove = True
        file_path = file.path
        self.assertTrue(file.exists())
        self.assertEqual(File(file.path).size().in_bytes(), 0)
        self.assertTrue(str(file.path).startswith(str(temp_dir.path)))
        self.assertTrue(file.name.startswith("the-test-prefix-"))
        self.assertTrue(file.name.endswith("-the-test-suffix"))
        file.__del__()
        del file
        self.assertFileDoesNotExist(file_path)
        self.assertTrue(File(path).exists())

    def test_can_create_and_destroy_temporary_file_with_ctx_mngr(self):
        path = self.create_path("temp-test-file")
        file = TemporaryFile(path, auto_remove=False)
        self.assertFileDoesNotExist(path)
        with file:
            file.create()
            self.assertTrue(File(path).exists())

        self.assertFileDoesNotExist(path)

    def test_can_create_temporary_file_in_temp_sys_location(self):
        file = TemporaryFile.create_temporary_file(
            prefix="the-test-prefix-",
            suffix="-the-test-suffix"
        )
        file.auto_remove = True
        file_path = file.path
        self.assertTrue(file.exists())
        self.assertEqual(File(file.path).size().in_bytes(), 0)
        path_str = str(file.path)
        expected_tmp_dir = f"{self.drive}{self.sep}tmp{self.sep}"
        self.assertTrue(path_str.startswith(expected_tmp_dir))
        self.assertTrue(file.name.startswith("the-test-prefix-"))
        self.assertTrue(file.name.endswith("-the-test-suffix"))
        file.__del__()
        del file
        self.assertFileDoesNotExist(file_path)

    def test_can_create_temporary_directory(self):
        file = TemporaryFile.create_temporary_directory()
        file_path = file.path
        self.assertTrue(file.exists())
        path_str = str(file.path)
        expected_tmp_dir = f"{self.drive}{self.sep}tmp{self.sep}"
        self.assertTrue(path_str.startswith(expected_tmp_dir))
        file.__del__()
        del file
        self.assertTrue(File(file_path).is_directory())

    def test_can_create_temporary_directory_with_auto_remove(self):
        file = TemporaryFile.create_temporary_directory()
        file.auto_remove = True
        file_path = file.path
        self.assertTrue(file.exists())
        path_str = str(file.path)
        expected_tmp_dir = f"{self.drive}{self.sep}tmp{self.sep}"
        self.assertTrue(path_str.startswith(expected_tmp_dir))
        file.__del__()
        del file
        self.assertFileDoesNotExist(file_path)

    def test_can_create_temporary_directory_with_prefix(self):
        file = TemporaryFile.create_temporary_directory(
            prefix="the-test-prefix-"
        )
        file.auto_remove = True
        file_path = file.path
        self.assertTrue(file.exists())
        self.assertTrue(file.name.startswith("the-test-prefix-"))
        file.__del__()
        del file
        self.assertFileDoesNotExist(file_path)

    def test_can_create_temporary_directory_with_suffix(self):
        file = TemporaryFile.create_temporary_directory(
            suffix="-the-test-suffix"
        )
        file.auto_remove = True
        file_path = file.path
        self.assertTrue(file.exists())
        self.assertTrue(file.name.endswith("-the-test-suffix"))
        file.__del__()
        del file
        self.assertFileDoesNotExist(file_path)

    def test_can_create_temporary_directory_with_prefix_and_suffix(self):
        file = TemporaryFile.create_temporary_directory(
            prefix="the-test-prefix-",
            suffix="-the-test-suffix"
        )
        file.auto_remove = True
        file_path = file.path
        self.assertTrue(file.exists())
        self.assertTrue(file.name.startswith("the-test-prefix-"))
        self.assertTrue(file.name.endswith("-the-test-suffix"))
        file.__del__()
        del file
        self.assertFileDoesNotExist(file_path)

    def test_repr_returns_file_with_relative_path(self):
        path_string = str(PurePath("user/test-file"))
        file = File(path_string)
        self.assertEqual(repr(file), f"File('{path_string}')")

    def test_repr_returns_file_with_absolute_path(self):
        expected_path = (
            f"{self.drive}{self.sep}home{self.sep}user{self.sep}test-file"
        )
        path_string = str(PurePath("/home/user/test-file"))
        file = File(path_string)
        self.assertEqual(repr(file), f"File('{expected_path}')")

    def test_repr_returns_file_with_root_path(self):
        file = File("/")
        expected_value = f"File('{self.drive}{self.sep}')"
        self.assertEqual(repr(file), expected_value)
        file = File("C:\\")
        expected_value = f"File('C:{self.sep}')"
        self.assertEqual(repr(file), "File('C:\\')")

    def test_repr_distinguishes_different_paths(self):
        file_a = File("/foo/bar.txt")
        file_b = File("/foo/baz.txt")
        self.assertNotEqual(repr(file_a), repr(file_b))


if __name__ == "__main__":
    TestCase.run_tests()
