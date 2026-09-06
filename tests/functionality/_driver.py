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
"""Functionality testing facilities.

Provides driver classes that allow functionality tests to programmatically
start and interact with the Fathom client and server applications.

The `ClientDriver` executes the Fathom CLI client in-process and captures
its stdout/stderr output. The `ServerDriver` launches the Fathom server in
a separate process and manages its lifecycle.
"""

import io
import multiprocessing

from contextlib import redirect_stdout, redirect_stderr
from typing import Optional, Final

from raven.fathom.base import ApplicationContext, ApplicationMode
from raven.fathom.base import File
from raven.fathom.client.cli.application import main as client_main
from raven.fathom.server.cli import main as server_main
from raven.fathom.server.datastore import DatabaseManager
from raven.fathom.server.dao.api import DataAccess
from raven.fathom.server.defaults import DEFAULT_SERVER_PORT
from raven.fathom.server.defaults import SERVER_ROOT_PATH_V1

from tests.functionality._env import ClientEnvironment, ServerEnvironment


_TEST_RES_DIR = File(__file__).get_parent_directory() / "fixtures/res"

# Default timeout in seconds when waiting for the server to become ready.
_SERVER_READY_TIMEOUT: Final = 15.0

# Timeout in seconds for a graceful server shutdown before force-killing.
_SERVER_SHUTDOWN_TIMEOUT: Final = 5.0


class ServerStartupException(Exception):
    """Raised when the Fathom server fails to start within the expected
    time or the server process terminates prematurely.
    """


class ClientDriver:
    """Driver for the Fathom client in functionality tests.

    Executes the Fathom client in-process (same Python interpreter of
    the caller) and captures its stdout and stderr output. This allows tests
    to both inspect the exit status and assert on the textual output produced
    by the client.

    A fresh `ClientDriver` should be created for each test method to
    ensure isolation. The `TestCase` base class handles this automatically.
    """

    def __init__(self, env: ClientEnvironment):
        self._env = env
        self._exit_status: Optional[int] = None
        self._stdout: str = ""
        self._stderr: str = ""
        self._has_executed: bool = False

    @property
    def env(self) -> ClientEnvironment:
        """The `SystemEnvironment` implementation used by the Fathom client
        during functionality tests.
        """
        return self._env

    @property
    def exit_status(self) -> Optional[int]:
        """The exit status of the last client execution.

        Is `None` if `execute()` has not been called yet.
        """
        return self._exit_status

    @property
    def stdout(self) -> str:
        """The captured stdout output of the last client execution.

        Is an empty string if `execute()` has not been called yet.
        """
        return self._stdout

    @property
    def stderr(self) -> str:
        """The captured stderr output of the last client execution.

        Is an empty string if `execute()` has not been called yet.
        """
        return self._stderr

    def execute(self, *args: str):
        """Executes the Fathom CLI client with the given arguments.

        The client runs in-process. Its stdout and stderr are captured and
        made available via the `stdout` and `stderr` properties. The exit
        status is available via `exit_status`.

        Args:
            args: The CLI arguments to pass to the client, e.g. ``"deploy"``.
                The program name (``"fathom"``) is prepended automatically.
        """
        exec_args = ["fathom"] + list(args)
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
            self._exit_status = int(client_main(exec_args))

        self._stdout = stdout_buffer.getvalue()
        self._stderr = stderr_buffer.getvalue()
        self._has_executed = True

    def has_executed(self) -> bool:
        """Checks whether the client has been executed at least once.

        Returns:
            bool: `True` if `execute()` has been called.
        """
        return self._has_executed


class ServerDriver:
    """Driver for the Fathom server in functionality tests.

    Launches the Fathom server in a child process and manages its
    lifecycle. The server is started via `execute()` and stopped via
    `shutdown()`. The `TestCase` base class takes care of starting a
    fresh server before each test method and shutting it down after
    that method completes.
    """

    def __init__(self, env: ServerEnvironment):
        self._env = env
        self._stdout: str = ""
        self._stderr: str = ""
        self._exit_status: Optional[int] = None
        self._command_exit_status: Optional[int] = None
        self._proc: Optional[multiprocessing.Process] = None

    @property
    def env(self) -> ServerEnvironment:
        """The `SystemEnvironment` implementation used by the Fathom server
        during functionality tests.
        """
        return self._env

    @property
    def exit_status(self) -> Optional[int]:
        """The exit status of the Fathom server process.

        This is the exit status of the server process itself, not of any
        server CLI commands executed via `execute()`. It is set after the
        server process terminates.

        Is `None` if the server has not yet terminated.
        """
        return self._exit_status

    @property
    def command_exit_status(self) -> Optional[int]:
        """The exit status of the last run Fathom server CLI command.

        Is `None` if no server CLI command has been executed yet.
        """
        return self._command_exit_status

    @property
    def stdout(self) -> str:
        """The captured stdout output of the last server command execution.

        This is the captured stdout output of the last server
        command executed via `execute()`.

        Is an empty string if `execute()` has not been called yet.
        """
        return self._stdout

    @property
    def stderr(self) -> str:
        """The captured stderr output of the last server command execution.

        This is the captured stderr output of the last server
        command executed via `execute()`.

        Is an empty string if `execute()` has not been called yet.
        """
        return self._stderr

    @property
    def datastore(self) -> DataAccess:
        """The data access object of the Fathom server.

        Returns:
            DataAccess: The data access object.
        """
        with ApplicationContext.create_instance().initialize(
            ApplicationMode.TESTING, File(self._env.cwd)
        ):
            db_manager = DatabaseManager()
            db_manager.locate_application_database()
            db = db_manager.get_database()
            if not db.is_connected():
                db.connect()

            return DataAccess.instance()

    def is_running(self) -> bool:
        """Checks whether the server process is currently running.

        Returns:
            bool: `True` if the server process is alive.
        """
        return self._proc is not None and self._proc.is_alive()

    def get_root_path(self) -> str:
        """Returns the root path of the Fathom server application.

        Returns:
            str: The base path component under which the server application
                is being served. Has a leading '/' character.
        """
        return SERVER_ROOT_PATH_V1

    def get_default_port(self) -> int:
        """Returns the network port used by the Fathom server by default.

        Returns:
            int: The default server port.
        """
        return DEFAULT_SERVER_PORT

    def initialize_datastore(self, sql_file: Optional[str] = None):
        """Initializes the server datastore before the server process starts.

        Creates the database schema and, optionally, pre-populates it with
        data from a SQL file. Must be called before `execute()` so that the
        server finds an existing database on startup and skips its own
        built-in seeding.

        Args:
            sql_file (str): Path to a ``.sql`` file containing arbitrary SQL
                statements to load into the database. If ``None``, the schema
                is created but left empty.
        """
        if self.is_running():
            raise RuntimeError(
                "Cannot initialize datastore while server is running. "
                "You must call initialize_datastore() before `execute()`."
            )

        with ApplicationContext.create_instance().initialize(
            ApplicationMode.TESTING, File(self._env.cwd)
        ):
            db_manager = DatabaseManager()
            db_manager.locate_application_database()
            db = db_manager.get_database()
            db.connect()
            db_manager.initialize_empty_database()
            if sql_file is not None:
                file = File(sql_file)
                if not file.path.is_absolute():
                    file = _TEST_RES_DIR / file

                sql = file.read_all_text()
                db.run_command(sql)

            db.disconnect()

    def disconnect_datastore(self):
        """Releases resources and shuts down the datastore."""
        db_manager = DatabaseManager()
        db_manager.shutdown()

    def execute(self, *args: str):
        """Executes a Fathom server CLI command with the given arguments.

        The server command runs in-process. Its stdout and stderr are captured
        and made available via the `stdout` and `stderr` properties. The exit
        status is available via `command_exit_status`.

        Args:
            args: The CLI arguments to pass to the server.
        """
        work_dir = str(self._env.get_current_working_directory())
        exec_args = [
            "fathom-server",
            "--working-directory",
            work_dir
        ] + list(args)

        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
            self._command_exit_status = int(server_main(exec_args))

        self._stdout = stdout_buffer.getvalue()
        self._stderr = stderr_buffer.getvalue()

    def start(self, args: list[str]):
        """Starts the Fathom server in a child process.

        Blocks until the server signals that it is ready to accept
        requests, or until the startup timeout expires.

        Args:
            args: The CLI arguments to pass to the server.
                The program name (``"fathom-server"``) is prepended
                automatically.

        Raises:
            ServerStartupException: If the server does not become ready
                within the timeout or the server process dies during
                startup.
        """
        if self.is_running():
            raise ServerStartupException(
                "Server is already running"
            )

        event_server_ready = multiprocessing.Event() # Must be the last arg
        exec_args = ["fathom-server"] + args + [event_server_ready]
        self._proc = multiprocessing.Process(
            target=server_main,
            name="Fathom-Server-1",
            args=(exec_args,),
            daemon=True,
        )
        self._proc.start()
        is_ready = event_server_ready.wait(timeout=_SERVER_READY_TIMEOUT)
        if not is_ready:
            alive = self._proc.is_alive()
            self._force_shutdown()
            if not alive:
                raise ServerStartupException(
                    "Server process terminated prematurely during startup "
                    f"(exit code: {self._exit_status})"
                )

            raise ServerStartupException(
                f"Server did not become ready within "
                f"{_SERVER_READY_TIMEOUT} seconds"
            )

        if not self._proc.is_alive():
            raise ServerStartupException(
                "Server process terminated immediately after signalling "
                f"ready (exit code: {self._exit_status})"
            )

    def shutdown(self):
        """Shuts down the server process gracefully.

        Sends a SIGTERM to the server process and waits up to
        `_SERVER_SHUTDOWN_TIMEOUT` seconds for it to exit. If the process
        does not terminate within that time, it is forcefully killed.

        After shutdown, `exit_status` reflects the process exit code.
        """
        if self._proc is None:
            return

        if self._proc.is_alive():
            self._proc.terminate()
            self._proc.join(timeout=_SERVER_SHUTDOWN_TIMEOUT)
            if self._proc.is_alive():
                self._force_shutdown()

        if self._proc is not None:
            self._exit_status = self._proc.exitcode
            self._proc = None

    def restart(self, args: Optional[list[str]] = None):
        """Restarts the server process.

        Shuts down the currently running server (if any) and starts
        a new one with the given arguments.

        Args:
            args: The CLI arguments to pass to the server. Defaults to
                an empty argument list.

        Raises:
            ServerStartupException: If the server does not become ready
                within the timeout.
        """
        self.shutdown()
        self.start(args or [])

    def _force_shutdown(self):
        """Forcefully terminates the server process without waiting."""
        if self._proc is not None:
            try:
                self._proc.kill()
            except OSError:
                pass
            self._proc.join(timeout=2.0)
            self._exit_status = self._proc.exitcode
            self._proc = None
