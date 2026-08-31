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
"""Fathom client logging utilities."""

from typing import TYPE_CHECKING, Final

from raven.fathom.base import SystemEnvironment
from raven.fathom.base import ApplicationContext, ApplicationMode
from raven.fathom.base import File
from raven.fathom.base.context import APPLICATION_PROJECT_ID
from raven.fathom.base.logging import LogManager, LogLevel
from raven.fathom.base.logging import LogFormatterCLI
from raven.fathom.base.logging import LogHandlerCLI, LogHandlerFile
from raven.fathom.base.logging import Logger as BaseLogger

if TYPE_CHECKING:
    from raven.fathom.client.cli import ArgumentsCLI


FATHOM_CLIENT_LOGGER_NAME: Final[str] = "raven.fathom.client"


def _determine_log_level(args: "ArgumentsCLI") -> LogLevel:
    log_level = LogLevel.INFO
    log_verbose = args.verbose
    if log_verbose:
        log_level = LogLevel.VERBOSE

    log_debug = args.debug
    if log_debug:
        log_level = LogLevel.DEBUG

    return log_level


def setup_cli_logger(args: "ArgumentsCLI"):
    """Setup function for the CLI logging utilities.

    This function should only be called once during startup.

    Args:
        args (ArgumentsCLI): The CLI arguments given to the application.
            Is used to determine the logging configuration.
    """
    ctx = ApplicationContext.instance()
    LogManager().setup_logger(
        FATHOM_CLIENT_LOGGER_NAME,
        _determine_log_level(args),
        LogHandlerCLI(),
        LogFormatterCLI(
            use_colours=ctx.get_application_mode() != ApplicationMode.TESTING
        ),
    )


def setup_file_logger(args: "ArgumentsCLI"):
    """Setup function for the file logging utilities.

    This function should only be called once during startup.

    Args:
        args (ArgumentsCLI): The CLI arguments given to the application.
            Is used to determine the logging configuration.

    Raises:
        FileIOException: If the log file could not be created.
    """
    env = SystemEnvironment.instance()
    base_dir = env.get_variable("XDG_STATE_HOME")
    if not base_dir or not File(base_dir).path.is_absolute():
        base_dir = env.get_home_path()
        if base_dir:
            base_dir /= ".local/state"

    if base_dir:
        base_dir = File(base_dir)
        app_dir = File(APPLICATION_PROJECT_ID)
        log_file = File("client.log")
        log_file_path = base_dir / app_dir / log_file
        log_file_path.get_parent_directory().create_directory_tree()
        LogManager().setup_logger(
            FATHOM_CLIENT_LOGGER_NAME,
            _determine_log_level(args),
            LogHandlerFile(log_file_path),
            LogFormatterCLI(use_colours=False),
        )


def shutdown_loggers():
    """Shutdown function for the logging utilities."""
    LogManager().shutdown_loggers()


class Logger(BaseLogger):
    """Fathom client logger."""

    @staticmethod
    def get() -> BaseLogger:
        """Obtains a Fathom client logger.
        
        Returns:
            Logger: A `Logger` object for the Fathom client.
        """
        return BaseLogger.get_logger(FATHOM_CLIENT_LOGGER_NAME)
