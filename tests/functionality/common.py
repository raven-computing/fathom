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
"""Common functionality test code.

This module provides the `TestCase` base class for all Fathom functionality
(end-to-end) tests. Functionality tests interact with the real filesystem
and perform actual networking between the Fathom client and server, but
confine all filesystem operations to a ``testing`` subdirectory within the
project build tree so that test artifacts can be easily cleaned up.

Typical usage::

    from tests.functionality import TestCase
    from tests.fixtures import ProjectFixture

    class TestMyFeature(TestCase, ProjectFixture):

        def test_something(self):
            self.client.execute(["deploy"])
            self.assertClientSuccess()
"""

# pylint: disable=C0103

import os

from pathlib import PurePath
from typing import Optional, Final

from raven.fathom.base import Dependencies
from raven.fathom.base import File, URL, MethodHTTP, RequestHTTP
from raven.fathom.base.context import _ENV_VAR_FATHOM_TEST_MODE
from raven.fathom.base.context import _BUILD_DIRECTORY
from raven.fathom.base.context import _TESTING_DIRECTORY
from raven.fathom.base.context import _ENV_VAR_ENABLED
from raven.fathom.base.context import get_project_source_root
from raven.fathom.base.decorators._singleton import _SingletonAllocator

from tests.common import FathomTestCase
from tests.functionality._driver import ClientDriver, ServerDriver
from tests.functionality._driver import ServerStartupException
from tests.functionality._env import ClientEnvironment, ServerEnvironment


__all__ = [
    "PROJECT_DIR",
    "TESTING_DIRECTORY",
    "TestCase",
]


PROJECT_DIR: Final = get_project_source_root()
assert PROJECT_DIR, "Failed to determine project root path"

# The absolute path to the directory where all files are
# written during functionality tests.
TESTING_DIRECTORY: Final = PROJECT_DIR / _BUILD_DIRECTORY / _TESTING_DIRECTORY


def clean_testing_directory():
    """Removes and recreates the testing directory.

    This deletes the testing directory and recreates a fresh empty directory.
    Useful for a clean-slate setup before running the entire
    functionality test suite.
    """
    testing_directory = TESTING_DIRECTORY
    if testing_directory.exists():
        testing_directory.remove()

    testing_directory.create_directory_tree()


class TestCase(FathomTestCase):
    """Base class of functionality test cases.

    Manages the lifecycle of a Fathom server and client for end-to-end
    testing:

    * Method level (`setUp()` / `tearDown()`): A fresh server and
      client are created for each test method. The server is started
      before the test body runs and shut down after it completes,
      ensuring full isolation between test methods.

    Subclasses may set the class attribute ``_AUTO_START_SERVER = False``
    to skip the automatic server startup, e.g. for tests that only
    exercise offline client functionality.
    """

    _AUTO_START_SERVER: bool = True

    # Optional path to a .sql file used to pre-populate the server datastore
    # before the server process starts. When set, the schema is created and
    # the SQL file is executed against the database so that the server finds
    # an existing, ready-to-use datastore on startup. When None, the server
    # initializes the datastore itself (default behaviour).
    _DATASTORE_SQL_FILE: Optional[str] = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Dependencies.enable_object_store()
        Dependencies.flush_object_store()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        Dependencies.disable_object_store()

    def setUp(self):
        super().setUp()
        clean_testing_directory()
        self._set_up_server()
        self._set_up_client()

    def tearDown(self):
        if self._server is not None:
            self._server.shutdown()
            self._server.disconnect_datastore()
            self._server = None # pylint: disable=W0201

        _SingletonAllocator._singleton_purge() # pylint: disable=W0212

    @property
    def server(self) -> ServerDriver:
        """The server driver instance set up for the test case."""
        assert self._server is not None, "Server driver is not initialized"
        return self._server

    @property
    def client(self) -> ClientDriver:
        """The client driver instance set up for the test case."""
        assert self._client is not None, "Client driver is not initialized"
        return self._client

    def http(self, method: MethodHTTP, path: str) -> RequestHTTP:
        """Creates an HTTP request to the Fathom server for the given path.

        Use `RequestHTTP.send()` to send the request and receive a response.

        Args:
            method (MethodHTTP): The HTTP method to use.
            path (str): The URL path for the HTTP request, relative to
                the Fathom server base path.

        Returns:
            RequestHTTP: The created but unsent HTTP request.
        """
        url = URL()
        url.scheme = "http"
        url.authority.hostname = "localhost"
        url.authority.port = self.server.get_default_port()
        base = self.server.get_root_path()
        url.path = base.rstrip("/") + "/" + path.lstrip("/")
        return RequestHTTP(method, url)

    def get_client_directory(self) -> File:
        """Returns the client working directory for the current test.

        Returns:
            File: The absolute path to the client working directory.
        """
        return File(self.client.env.get_current_working_directory())

    def get_server_directory(self) -> File:
        """Returns the server working directory for the current test.

        Returns:
            File: The absolute path to the server working directory.
        """
        return File(self.server.env.get_current_working_directory())

    def create_test_file(self, file, content=None) -> File:
        """Creates a file under the client working directory.

        Parent directories are created automatically. If the file already
        exists, it is overwritten.

        Args:
            file: A file with a relative path (`str`, `PurePath` or `File`)
                to create, resolved against the client working directory.
            content: Optional content to write. If given as `str`, it is
                written as UTF-8 text. If given as `bytes`, it is written
                as binary. If `None`, an empty file is created.

        Returns:
            File: The created file.
        """
        file = File(file)
        assert not file.path.is_absolute()
        target = self.get_client_directory() / file
        target.get_parent_directory().create_directory_tree()
        target.write_all("" if content is None else content)
        return target

    def create_test_directory(self, directory) -> File:
        """Creates a directory under the client working directory.

        All intermediate directories are created as needed.

        Args:
            directory: A relative path (`str`, `PurePath` or `File`) for the
                directory to create, resolved against the client working
                directory.

        Returns:
            File: The created directory.
        """
        directory = File(directory)
        assert not directory.path.is_absolute()
        target = self.get_client_directory() / directory
        target.create_directory_tree()
        return target

    def read_test_file(self, file) -> str:
        """Reads a text file under the client working directory.

        Args:
            file: A relative path to the file, resolved against
                the client working directory.

        Returns:
            str: The text content of the file (UTF-8).
        """
        file = File(file)
        assert not file.path.is_absolute()
        target = self.get_client_directory() / file
        return target.read_all_text()

    def _set_up_server(self):
        Dependencies.flush_object_store_type(ServerEnvironment)
        env = ServerEnvironment.instance()
        env.cwd = PurePath(TESTING_DIRECTORY / "server")
        cwd = File(env.cwd)

        cwd.create_directory_tree()

        env.env_vars[_ENV_VAR_FATHOM_TEST_MODE] = _ENV_VAR_ENABLED
        # Windows uses spawn start method instead of fork, so the test mode
        # must actually be defined in the OS environment otherwise the
        # test server will not see it
        os.environ[_ENV_VAR_FATHOM_TEST_MODE] = _ENV_VAR_ENABLED

        server = ServerDriver(env)
        if self._AUTO_START_SERVER:
            if self._DATASTORE_SQL_FILE is not None:
                server.initialize_datastore(self._DATASTORE_SQL_FILE)

            server.execute([])
            if not server.is_running():
                raise ServerStartupException(
                    "Server process is not running after execute()"
                )

        self._server = server

    def _set_up_client(self):
        Dependencies.flush_object_store_type(ClientEnvironment)
        env = ClientEnvironment.instance()
        env.cwd = PurePath(TESTING_DIRECTORY / "client")
        env.home = PurePath(TESTING_DIRECTORY / "user")
        cwd = File(env.cwd)
        if cwd.exists():
            cwd.remove()

        cwd.create_directory_tree()

        home = File(env.home)
        if home.exists():
            home.remove()

        home.create_directory_tree()

        env.env_vars[_ENV_VAR_FATHOM_TEST_MODE] = _ENV_VAR_ENABLED
        env.env_vars["XDG_STATE_HOME"] = ""
        self._client = ClientDriver(env)

    def assertClientSuccess(self, msg: Optional[str] = None):
        """Asserts that the client exited with status code 0.

        Args:
            msg (str): Optional failure message override.

        Raises:
            AssertionError: If the client has not been executed or exited
                with a non-zero status.
        """
        status = self.client.exit_status
        if status is None:
            raise AssertionError(
                msg or "Client has not been executed yet"
            )

        if status != 0:
            detail = (
                f"Client exited with status {status}.\n"
                f"stdout: {self.client.stdout!r}\n"
                f"stderr: {self.client.stderr!r}"
            )
            raise AssertionError(msg or detail)

    def assertClientFailure(self, msg: Optional[str] = None):
        """Asserts that the client exited with a non-zero status code.

        Args:
            msg (str): Optional failure message override.

        Raises:
            AssertionError: If the client has not been executed or exited
                with status 0.
        """
        status = self.client.exit_status
        if status is None:
            raise AssertionError(
                msg or "Client has not been executed yet"
            )

        if status == 0:
            raise AssertionError(
                msg or "Expected client to fail but it exited with status 0"
            )

    def assertClientExitStatus(
        self,
        expected_status: int,
        msg: Optional[str] = None
    ):
        """Asserts that the client exited with the given status code.

        Args:
            expected_status (int): The expected exit status.
            msg (str): Optional failure message override.

        Raises:
            AssertionError: If the exit status does not match.
        """
        status = self.client.exit_status
        if status is None:
            raise AssertionError(
                msg or "Client has not been executed yet"
            )

        if status != expected_status:
            raise AssertionError(
                msg or (
                    f"Expected client exit status {expected_status}, "
                    f"got {status}"
                )
            )

    def assertClientStdoutContains(self, text: str, msg: Optional[str] = None):
        """Asserts that the client stdout contains the given text.

        Args:
            text (str): The text to search for in stdout.
            msg (str): Optional failure message override.
        """
        if text not in self.client.stdout:
            raise AssertionError(
                msg or (
                    "Expected that the stdout of the client "
                    f"contains the following text:\n{text!r}.\n"
                )
            )

    def assertClientStderrContains(self, text: str, msg: Optional[str] = None):
        """Asserts that the client stderr contains the given text.

        Args:
            text (str): The text to search for in stderr.
            msg (str): Optional failure message override.
        """
        if text not in self.client.stderr:
            raise AssertionError(
                msg or (
                    "Expected that the stderr of the client "
                    f"contains the following text:\n{text!r}.\n"
                )
            )

    def assertServerIsRunning(self, msg: Optional[str] = None):
        """Asserts that the server process is currently running.

        Args:
            msg (str): Optional failure message override.

        Raises:
            AssertionError: If the server process is not alive.
        """
        if not self.server.is_running():
            raise AssertionError(
                msg or "Expected server to be running"
            )

    def assertFileExists(self, path):
        """Asserts that a file exists at the given path.

        Args:
            path: An absolute or relative path. Relative paths are resolved
                against the client working directory.

        Raises:
            AssertionError: If the file does not exist.
        """
        path = self._resolve_path(path)
        if not File(path).exists():
            raise AssertionError(
                f"Expected file '{path}' to exist"
            )

    def assertFileDoesNotExist(self, path):
        """Asserts that no file exists at the given path.

        Args:
            path: An absolute or relative path. Relative paths are resolved
                against the client working directory.

        Raises:
            AssertionError: If the file exists.
        """
        path = self._resolve_path(path)
        if File(path).exists():
            raise AssertionError(
                f"Expected file '{path}' to not exist"
            )

    def assertDirectoryExists(self, path):
        """Asserts that a directory exists at the given path.

        Args:
            path: An absolute or relative path. Relative paths are resolved
                against the client working directory.

        Raises:
            AssertionError: If the path does not exist or is not a
                directory.
        """
        path = self._resolve_path(path)
        if not File(path).is_directory():
            raise AssertionError(
                f"Expected '{path}' to be an existing directory"
            )

    def assertFileContent(self, path, expected_data):
        """Asserts that a file contains the expected data.

        Args:
            path: An absolute or relative path. Relative paths are resolved
                against the client working directory.
            expected_data: The expected content as `str` (compared as
                UTF-8 text) or `bytes` (compared as raw bytes).

        Raises:
            AssertionError: If the file content does not match.
        """
        path = self._resolve_path(path)
        file = File(path)
        if not file.exists():
            raise AssertionError(
                f"Cannot assert content: File '{path}' does not exist"
            )

        if isinstance(expected_data, bytes):
            actual = file.read_all_bytes()
        else:
            actual = file.read_all_text()

        if actual != expected_data:
            raise AssertionError(
                f"File content of '{path}' does not match expected data.\n"
                f"Expected: {expected_data!r}\n"
                f"Actual:   {actual!r}"
            )

    def assertDirectoryContent(self, path, expected_names):
        """Asserts that a directory contains exactly the expected entries.

        Only checks immediate children (non-recursive). The comparison is
        done on entry names as a set of strings.

        Args:
            path: An absolute or relative path. Relative paths are resolved
                against the client working directory.
            expected_names (set): A set of file/directory name strings
                expected to be present.

        Raises:
            AssertionError: If the directory contents do not match.
        """
        path = self._resolve_path(path)
        file = File(path)
        if not file.is_directory():
            raise AssertionError(
                f"Cannot assert directory content: '{path}' is not "
                "an existing directory"
            )

        actual_names = set(entry.name for entry in file.list_files())
        if actual_names != expected_names:
            missing = expected_names - actual_names
            unexpected = actual_names - expected_names
            parts = [
                f"Directory content of '{path}' does not match "
                "expected entries."
            ]
            if missing:
                parts.append(f"Missing:    {missing}")
            if unexpected:
                parts.append(f"Unexpected: {unexpected}")

            raise AssertionError("\n".join(parts))

    def _resolve_path(self, path) -> PurePath:
        """Resolves a path, making relative paths absolute against
        the client working directory.
        """
        path = PurePath(path)
        if not path.is_absolute():
            path = self.client.env.get_current_working_directory() / path

        return path
