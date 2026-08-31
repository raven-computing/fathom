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
"""Fathom server application context."""

from typing import Final

from raven.fathom.base import SystemEnvironment, ApplicationMode
from raven.fathom.base import File, FileIOException
from raven.fathom.base.decorators import noexcept
from raven.fathom.base.context import determine_application_mode
from raven.fathom.base.context import determine_working_directory
from raven.fathom.base.context import APPLICATION_PROJECT_ID
from raven.fathom.server.logging import log_stderr


_ENV_VAR_FATHOM_HOME: Final[str] = "A_FATHOM_HOME"

_DOT_FATHOM_HOME: Final[File] = File(f".{APPLICATION_PROJECT_ID}_home")

_FATHOM_SERVER_SUBDIR: Final[File] = File("server")


@noexcept
def _check_is_fathom_home_at(directory: File) -> bool:
    dot_fathom_home_file = directory / _DOT_FATHOM_HOME
    if dot_fathom_home_file.is_regular_file():
        try:
            file_is_empty = dot_fathom_home_file.is_empty()
            if not file_is_empty:
                log_stderr(
                    "WARNING: "
                    f"File is not empty: '{dot_fathom_home_file}'"
                )
                log_stderr(
                    "The regular file indicative of "
                    "the Fathom server home directory should be empty."
                )

            return file_is_empty
        except FileIOException as ex:
            log_stderr(
                "WARNING: A file I/O error has occurred while checking "
                f"for a Fathom server home file at: '{dot_fathom_home_file}'"
            )
            log_stderr(str(ex))
            log_stderr(
                "If you intend to run in a PRODUCTION environment then the "
                "application might detect the wrong mode. "
                "This might not be suitable for production."
            )
            return False

    return False


@noexcept
def determine_server_application_mode() -> ApplicationMode:
    """Determines the server application mode based on the environment.

    Returns:
        ApplicationMode: The determined application mode of the Fathom server.
    """
    env = SystemEnvironment.instance()
    mode = determine_application_mode(env)
    if mode != ApplicationMode.PRODUCTION:
        return mode

    app_home = env.get_variable(_ENV_VAR_FATHOM_HOME)
    if app_home:
        return ApplicationMode.PRODUCTION

    cwd = File(env.get_current_working_directory())

    if _check_is_fathom_home_at(cwd):
        return ApplicationMode.PRODUCTION

    # Fallback. Should not happen in a properly set up system.
    log_stderr(
        "WARNING: Running in development mode. "
        "This is not suitable for production."
    )
    return ApplicationMode.DEVELOPMENT


@noexcept
def determine_server_working_directory(app_mode: ApplicationMode) -> File:
    """Determines the working directory for the server application.

    Args:
        app_mode (ApplicationMode): The application mode.

    Returns:
        File: The working directory of the Fathom server.
    """
    env = SystemEnvironment.instance()
    if app_mode == ApplicationMode.PRODUCTION:
        app_home = env.get_variable(_ENV_VAR_FATHOM_HOME)
        if app_home:
            return File(app_home)

        cwd = File(env.get_current_working_directory())

        if _check_is_fathom_home_at(cwd):
            return cwd

    return determine_working_directory(env, app_mode) / _FATHOM_SERVER_SUBDIR
