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
"""Common integration test facilities."""

# pylint: disable=C0103

import os
import string
import tempfile
import shutil

from datetime import datetime
from pathlib import Path
from unittest import skip

from raven.fathom.server.datastore import DatabaseManager
from raven.fathom.server.models import User, UserPermission, Project
from raven.fathom.server.models import UserProjectRel
from raven.fathom.server.models import AuthDeployment

from tests.common import FathomTestCase


def skipIfNotZlibAvailable(reason=None):
    """Skips the test if the underlying Python interpreter does not have
    the zlib module available.

    Args:
        reason (str): The reason text informing why
            the decorated method was skipped.
    """
    def decorator(wrapped):
        return wrapped

    try:
        # pylint: disable=C0415,W0611
        import zlib
    except ImportError:
        return skip(reason or "")

    return decorator


def skipIfNotBz2Available(reason=None):
    """Skips the test if the underlying Python interpreter does not have
    the bz2 module available.

    Args:
        reason (str): The reason text informing why
            the decorated method was skipped.
    """
    def decorator(wrapped):
        return wrapped

    try:
        # pylint: disable=C0415,W0611
        import bz2
    except ImportError:
        return skip(reason or "")

    return decorator


def skipIfNotLzmaAvailable(reason=None):
    """Skips the test if the underlying Python interpreter does not have
    the lzma module available.

    Args:
        reason (str): The reason text informing why
            the decorated method was skipped.
    """
    def decorator(wrapped):
        return wrapped

    try:
        # pylint: disable=C0415,W0611
        import lzma
    except ImportError:
        return skip(reason or "")

    return decorator


class TestCase(FathomTestCase):
    """Base class for integration tests."""


class DatabaseIntegrationTestCase(TestCase):
    """Base class for all tests targeting database integrations."""

    def setUp(self):
        super().setUp()
        dbm = DatabaseManager()
        dbm.set_in_memory_storage(True)
        db = dbm.get_database()
        db.connect()
        dbm.initialize_empty_database()
        self.initialize_database()

    def tearDown(self):
        super().tearDown()
        db = DatabaseManager().get_database()
        db.disconnect()

    def initialize_database(self):
        """Concrete test cases may override this method to customize
        their database initialization.
        """
        test_user_id = User.create(
            identifier="test-user-1",
            name="Test User 1",
            password="123456",
        )
        UserPermission.create(
            user=test_user_id,
            allow_overwrite=True,
        )
        test_project_id = Project.create(
            identifier="test-project-1",
            name="Test Project 1",
            description="A Project for Testing Purposes (1).",
            latest_version="1.0.0",
            is_published=True,
        )
        UserProjectRel.create(
            user=test_user_id,
            project=test_project_id,
        )
        Project.create(
            identifier="test-project-2",
            name="Test Project 2",
            description="A Project for Testing Purposes (1).",
            latest_version="2.3.4",
            is_published=True,
        )
        AuthDeployment.create(
            token=string.ascii_lowercase + string.digits,
            expiration_time=datetime(2999, 12, 31),
            user=test_user_id,
            project=test_project_id,
            project_version=test_project_id.latest_version,
            allow_overwrite=True,
        )


class FileSystemIntegrationTestCase(TestCase):
    """Base class for all tests that need to interoperate
    or integrate with the filesystem.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        FileSystemIntegrationTestCase.TEST_DIR_PATH = Path(
            tempfile.mkdtemp(prefix="fathom-tests-")
        ).resolve()
        FileSystemIntegrationTestCase.TEST_DIR_CNT = 0

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        if cls.TEST_DIR_PATH and cls.TEST_DIR_PATH.exists():
            shutil.rmtree(cls.TEST_DIR_PATH)

    def setUp(self):
        super().setUp()
        self.testdir = (
            FileSystemIntegrationTestCase.TEST_DIR_PATH
            / Path(str(FileSystemIntegrationTestCase.TEST_DIR_CNT))
        )
        FileSystemIntegrationTestCase.TEST_DIR_CNT += 1
        self.testdir.mkdir()


    def create_path(self, file) -> Path:
        """Creates a path object for the given test file.

        The returned path will be absolute. If the given input path is already
        absolute, it is simply returned as a path object. If it is given as a
        file name or relative path, the returned file path will be located
        under a test directory.

        Args:
            file (str): The file to create a path object for.

        Returns:
            Path: The path to the given test file.
        """
        file = Path(file)
        if not file.is_absolute():
            file = self.testdir / file

        return file

    def create_path_str(self, file) -> str:
        """Creates a path string for the given test file.

        The returned path will be absolute. If the given input path is already
        absolute, it is simply returned as a path string. If it is given as a
        file name or relative path, the returned file path will be located
        under a test directory.

        Args:
            file (str): The file to create a string path for.

        Returns:
            str: The path to the given test file.
        """
        return str(self.create_path(file))

    def create_file(self, file, data=None, encoding="UTF-8") -> Path:
        """Creates a test file with the given path.

        Use this method to create a regular file under a temporary test
        directory which can be further used in a test case. The file should be
        specified as a relative path, or in the simplest case, just the
        name of the file. If the test file is specified as an absolute path,
        it is the responsibility of the caller to manage that file for the
        underlying test case.

        If `data` is not specified, the created file will be empty.

        Args:
            file (str): The relative path or name of the test file.
            data (bytes): The optional data content of the created file.
                Can be also specified as a `str`.
            encoding (str): The encoding of the text data to be saved to
                the file in case `data` is specified as a `str`.

        Returns:
            Path: The absolute path of the test file created.
        """
        path = self.create_path(file)
        path.touch()
        if data is not None:
            if isinstance(data, str):
                path.write_text(data, encoding=encoding)
            else:
                path.write_bytes(data)

        return path

    def create_directory(self, file):
        """Creates an empty test directory with the given path.

        Use this method to create a directory under a temporary test
        directory which can be further used in a test case. The file should be
        specified as a relative path, or in the simplest case, just the
        name of the directory. If the test directory is specified as an
        absolute path, it is the responsibility of the caller to manage that
        directory for the underlying test case.

        Any required parent directories will automatically be created.

        Args:
            file (str): The relative path or name of the test directory.

        Returns:
            Path: The absolute path of the test directory created.
        """
        path = self.create_path(file)
        path.mkdir(parents=True)
        return path

    def assertFileExists(self, file):
        """Asserts that the given file in fact exists in the filesystem.

        Args:
            file: The file to check, as a `Path` or `str`.

        Raises:
            AssertionError: If the given file does not exist.
        """
        if not self.create_path(file).exists():
            raise AssertionError(
                f"Expected that file '{file}' exists"
            )

    def assertFileDoesNotExist(self, file):
        """Asserts that the given file in fact does not exist in
        the filesystem.

        Args:
            file: The file to check, as a `Path` or `str`.

        Raises:
            AssertionError: If the given file does exist.
        """
        path = self.create_path(file)
        if os.path.lexists(path):
            raise AssertionError(
                f"Expected that file '{file}' does not exist"
            )

    def assertDirectoryExists(self, file):
        """Asserts that the given file exists in the filesystem and is
        in fact a directory.

        Args:
            file: The file to check, as a `Path` or `str`.

        Raises:
            AssertionError: If the given file does not exist
                or is not a directory.
        """
        if not self.create_path(file).is_dir():
            raise AssertionError(
                f"Expected that file '{file}' is a directory"
            )

    def assertFileSize(self, file, size_in_bytes):
        """Asserts that the given file has the expected size.

        Args:
            file: The file to check, as a `Path` or `str`.
            size_in_bytes (int): The expected size of the given file, in bytes.

        Raises:
            AssertionError: If the given file does not have the expected size.
        """
        self.assertEqual(size_in_bytes, self.create_path(file).stat().st_size)

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
        file_mode = "rb"
        if isinstance(expected_data, str):
            bin_mode = False
            file_mode = "rt"

        encoding = None if bin_mode else encoding
        with open(file, file_mode, encoding=encoding) as f:
            file_content = f.read()
            if file_content != expected_data:
                if bin_mode:
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

        file = str(file)
        actual_data = set()
        for item in os.walk(file):
            base = item[0][len(file)+1:]
            if base:
                base = Path(base).as_posix() + "/"

            actual_data |= set(base + directory for directory in item[1])
            actual_data |= set(base + reg_file for reg_file in item[2])

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
