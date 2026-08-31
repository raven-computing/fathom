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
"""Defines an application context that can be accessed throughout the program.

An application context is information pertaining to a specific instance of a
runnable program that usually applies globally to the entire application but
that is not part of the underlying operating system or platform environment.
"""

from __future__ import annotations

import threading

from enum import Enum
from pathlib import PurePath
from typing import Optional

from raven.fathom.base.decorators import noexcept
from raven.fathom.base.system import SystemEnvironment
from raven.fathom.base.file import File
from raven.fathom.base.exceptions import FathomBaseException


APPLICATION_NAME = "Fathom"

APPLICATION_PROJECT_ID = APPLICATION_NAME.lower()

_BUILD_DIRECTORY = "build"

_DEVELOPMENT_DIRECTORY = "devel"

_TESTING_DIRECTORY = "testing"

_ENV_VAR_FATHOM_TEST_MODE = "A_FATHOM_TEST_MODE"

_ENV_VAR_ENABLED = "1"

_ENV_VAR_DISABLED = "0"

_PROJECT_ROOT_FILE_CACHE = False


class ApplicationContextException(FathomBaseException):
    """An operation or request regarding the application context
    has failed or was invalid.
    """


class UninitializedApplicationException(ApplicationContextException):
    """A request was made with an uninitialized application context."""


class ApplicationInitializationException(ApplicationContextException):
    """The Fathom application could not be initialized."""


class ApplicationMode(Enum):
    """Enumeration of distinguishable application modes."""

    DEVELOPMENT = "Development"

    TESTING = "Testing"

    PRODUCTION = "Production"


@noexcept
def get_project_source_root() -> Optional[File]:
    """Gets the absolute path to the project root directory.

    This function is not MT-safe.

    Returns:
        File: The project root directory. May be `None` if this application
            is not run in either testing or development mode.
    """
    global _PROJECT_ROOT_FILE_CACHE  # pylint: disable=global-statement
    if _PROJECT_ROOT_FILE_CACHE is not False:
        return _PROJECT_ROOT_FILE_CACHE

    src_root = File(PurePath(__file__).parent.parent.parent.parent)
    setup_py = src_root / File("setup.py")
    pyproject_toml = src_root / File("pyproject.toml")
    if setup_py.is_regular_file() and pyproject_toml.is_regular_file():
        project_line = "# The Fathom Python project"
        # This is brittle
        if pyproject_toml.read_all_text().startswith(project_line):
            _PROJECT_ROOT_FILE_CACHE = src_root
            return src_root

    _PROJECT_ROOT_FILE_CACHE = None
    return None


@noexcept
def determine_application_mode(env: SystemEnvironment) -> ApplicationMode:
    """Determines the application mode based on the environment.

    Args:
        env (SystemEnvironment): The system environment injected by the caller.

    Returns:
        ApplicationMode: The determined application mode.
    """
    test_mode_env_var = env.get_variable(
        _ENV_VAR_FATHOM_TEST_MODE, default=_ENV_VAR_DISABLED
    )
    test_mode_enabled = test_mode_env_var == _ENV_VAR_ENABLED
    if test_mode_enabled:
        return ApplicationMode.TESTING

    if get_project_source_root() is not None:
        return ApplicationMode.DEVELOPMENT

    return ApplicationMode.PRODUCTION


@noexcept
def determine_working_directory(
    env: SystemEnvironment,
    app_mode: ApplicationMode
) -> File:
    """Determines the working directory for the application.

    Args:
        env (SystemEnvironment): The system environment injected by the caller.
        app_mode (ApplicationMode): The application mode.

    Returns:
        File: The working directory.
    """
    if app_mode == ApplicationMode.TESTING:
        src_root = get_project_source_root()
        assert src_root, "Source root path must be defined in testing mode"
        return src_root / File(_BUILD_DIRECTORY) / File(_TESTING_DIRECTORY)

    if app_mode == ApplicationMode.DEVELOPMENT:
        src_root = get_project_source_root()
        assert src_root, "Source root path must be defined in development mode"
        return src_root / File(_BUILD_DIRECTORY) / File(_DEVELOPMENT_DIRECTORY)

    if app_mode == ApplicationMode.PRODUCTION:
        return File(env.get_current_working_directory())

    # Dead code path
    assert False, f"Cannot determine working directory for mode '{app_mode}'"


class ApplicationContext:
    """Provides context data to an application.

    A production instance of an application should only have
    one `ApplicationContext` object, which is created at the start of the
    program and remains available until the program terminates.
    For testing purposes, the application context might be deliberately deleted
    and re-created multiple times during the lifetime of a program.

    Ordinary application code should not be concerned with context lifecycle
    management and should not create an `ApplicationContext` object directly
    but rather obtain an instance if needed via
    the `ApplicationContext.instance()` classmethod.
    """

    _instance: Optional["ApplicationContext"] = None
    _lock: threading.Lock = threading.Lock()

    def __init__(self):
        """Initializes a new `ApplicationContext` object.

        This initializer is private and should not be called directly.
        Initialization code of applications should use
        the `ApplicationContext.create_instance()` classmethod to create
        a new instance for the lifetime of the application.
        """
        self._init_mode = None
        self._dir_work = None
        self._init_lock = threading.Lock()

    def initialize(
        self,
        mode: ApplicationMode,
        work_dir: File
    ) -> "ApplicationContext":
        """Initializes the global application context.

        Args:
            mode (ApplicationMode): The mode for which to initialize
                the application.
            work_dir (File): The working directory of the application.

        Raises:
            ApplicationInitializationException: If the application context
                cannot be initialized.
        """
        with self._init_lock:
            if self._init_mode is not None:
                if self._init_mode == mode:
                    return self

                raise ApplicationInitializationException(
                    f"Cannot initialize application context for mode '{mode}':"
                    " Application was already initialized "
                    f"in mode '{self._init_mode}'"
                )

            self._dir_work = self._init_work_dir(mode, work_dir)
            self._init_mode = mode
            return self

    def get_application_mode(self) -> ApplicationMode:
        """Gets the mode of the running application.

        Returns:
            ApplicationMode: The mode of the application.
        """
        self._ensure_initialized()
        assert self._init_mode is not None
        return self._init_mode

    def get_application_name(self) -> str:
        """Gets the name of the running application.

        Returns:
            str: The name of the application.
        """
        return APPLICATION_NAME

    def get_project_identifier(self) -> str:
        """Gets the identifier of the application's project.

        Returns:
            str: The identifier of the project.
        """
        return APPLICATION_PROJECT_ID

    def get_working_directory(self) -> File:
        """Gets the working directory of the application.

        Returns:
            File: The working directory.
        """
        self._ensure_initialized()
        assert self._dir_work is not None
        return File(self._dir_work)

    def __enter__(self):
        return self

    def __exit__(self, ex_type, ex_value, ex_trace):
        ApplicationContext.delete()
        return False

    def _is_initialized(self):
        return self._init_mode is not None and self._dir_work is not None

    def _ensure_initialized(self):
        if not self._is_initialized():
            raise UninitializedApplicationException(
                "Cannot query application context state "
                "due to an uninitialized application context object. "
                "Did you forget to initialize the application context?"
            )

    def _init_work_dir(self, mode: ApplicationMode, work_dir: File):
        if not work_dir.path.is_absolute():
            raise ApplicationInitializationException(
                "Cannot initialize application context "
                "with relative working directory path. "
                f"Path must be absolute: '{work_dir}'"
            )

        if mode in (ApplicationMode.DEVELOPMENT, ApplicationMode.TESTING):
            if not work_dir.is_directory():
                work_dir.create_directory_tree()

        if not work_dir.is_directory():
            raise ApplicationInitializationException(
                f"Working directory '{work_dir}' does not exist "
                "or is not a directory"
            )

        return work_dir

    @classmethod
    def create_instance(cls) -> "ApplicationContext":
        """Creates and stores the global application context instance.

        Must be called exactly once per application lifetime, before any
        call to `instance()`. Typically used as a context manager via
        the `initialize()` method:

            ctx = ApplicationContext.create_instance()
            with ctx.initialize(mode, work_dir):
                ...

        Returns:
            ApplicationContext: The newly created `ApplicationContext` object.

        Raises:
            ApplicationInitializationException: If an instance already exists.
        """
        with cls._lock:
            if cls._instance is not None:
                raise ApplicationInitializationException(
                    "An ApplicationContext instance already exists. "
                    "ApplicationContext.create_instance() must only be called "
                    "once per application lifetime."
                )

            new_instance = cls()
            cls._instance = new_instance
            return new_instance

    @classmethod
    def delete(cls):
        """Deletes the global application context instance.

         This is only intended for testing purposes. The application context
         should typically be initialized once at the start of the program and
         remain available until the program terminates.
        """
        with cls._lock:
            cls._instance = None

    @classmethod
    def instance(cls) -> "ApplicationContext":
        """Gets the global application context.

        Returns:
            ApplicationContext: The `ApplicationContext` object.

        Raises:
            UninitializedApplicationException: If no instance has been
                created yet.
        """
        with cls._lock:
            if cls._instance is None:
                raise UninitializedApplicationException(
                    "No ApplicationContext instance exists. "
                    "Call ApplicationContext.create_instance() "
                    "before accessing the instance."
                )

            return cls._instance
