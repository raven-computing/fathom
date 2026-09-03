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
"""Fathom server logging utilities."""

import sys
import logging

from datetime import datetime
from typing import Final

import cherrypy

from raven.fathom.base import File, SystemEnvironment
from raven.fathom.base import ApplicationContext, ApplicationMode
from raven.fathom.base.context import ENV_VAR_FATHOM_DEBUG, _ENV_VAR_ENABLED
from raven.fathom.base.logging import LogManager, LogLevel
from raven.fathom.base.logging import LogFormatterCLI
from raven.fathom.base.logging import LogHandlerCLI, LogHandlerFile
from raven.fathom.base.logging import Logger as BaseLogger


FATHOM_SERVER_LOGGER_NAME: Final[str] = "raven.fathom.server"

FATHOM_SERVER_LOGS_DIRECTORY_NAME: Final[str] = "logs"

FATHOM_SERVER_LOG_FILE_NAME: Final[str] = "fathom.log"

FATHOM_LOG_FORMAT_TIMESTAMP: Final[str] = "%Y-%m-%dT%H:%M:%S"


class FathomLogHandlerFile(LogHandlerFile):
    """A `LogHandlerFile` for the Fathom server used for keeping log files."""

    def __init__(self):
        log_dir = Logger.server_log_file_directory()
        log_file = log_dir / FATHOM_SERVER_LOG_FILE_NAME
        super().__init__(log_file)


def log_stderr(message: str):
    """Logs a message to standard error.

    Is used to log messages that are not part of the Fathom server logging
    system, such as errors during startup.

    Args:
        message (str): The message to log.
    """
    print(message, file=sys.stderr)


def _setup_server_application_logging(args):
    log_level = LogLevel.INFO
    log_verbose = args.verbose
    if log_verbose:
        log_level = LogLevel.VERBOSE

    log_debug = args.debug
    if log_debug:
        log_level = LogLevel.DEBUG
    else:
        env = SystemEnvironment.instance()
        log_debug = env.get_variable(ENV_VAR_FATHOM_DEBUG)
        if log_debug == _ENV_VAR_ENABLED:
            log_level = LogLevel.DEBUG

    command = args.command
    handlers: list[logging.Handler] = []
    formatters: list[logging.Formatter] = []
    if command == "setup":
        handlers.append(LogHandlerCLI())
        formatters.append(LogFormatterCLI())
    else:
        handlers.append(FathomLogHandlerFile())
        formatters.append(LogFormatterServerApp())
        ctx = ApplicationContext.instance()
        if ctx.get_application_mode() == ApplicationMode.DEVELOPMENT:
            handlers.append(LogHandlerCLI())
            formatters.append(LogFormatterCLI(include_timestamp=True))

    LogManager().setup_logger(
        FATHOM_SERVER_LOGGER_NAME,
        log_level,
        handlers,
        formatters,
    )


def _setup_server_cherrypy_logging(args):
    # pylint: disable=W0212
    logger = cherrypy._cplogging.LogManager
    logger.time = lambda self: datetime.now().strftime(
        FATHOM_LOG_FORMAT_TIMESTAMP
    )
    logger.access_log_format = "{t} {h} {r} {s} {b} {f} {a}"
    log_dir = Logger.server_log_file_directory()
    cherrypy.log.access_file = str(log_dir / "access.log")
    cherrypy.log.error_file = str(log_dir / "server.log")
    ctx = ApplicationContext.instance()
    cherrypy.log.screen = (
        ctx.get_application_mode() == ApplicationMode.DEVELOPMENT
    )


def setup_server_logging(args):
    """Setup function for the server logging utilities.

    This function should only be called once during startup.

    Args:
        args (AppArgs): The arguments given to the server application.
            Is used to determine the logging configuration.

    Raises:
        FileIOException: If the directory where the server logs are
            stored cannot be created.
    """
    _setup_server_application_logging(args)
    _setup_server_cherrypy_logging(args)


def shutdown_loggers():
    """Shutdown function for the logging utilities."""
    LogManager().shutdown_loggers()


class LogFormatterServerApp(logging.Formatter):
    """A `logging.Formatter` used for server applications."""

    MSG_FORMAT: Final = "%(message)s"

    def __init__(self):
        super().__init__()
        msg_format = LogFormatterServerApp.MSG_FORMAT
        self.log_level_formatters = {
            logging.DEBUG: self._create_log_level_formatter(
                "DEBUG", msg_format
            ),
            logging.INFO: self._create_log_level_formatter(
                "INFO", msg_format
            ),
            logging.WARNING: self._create_log_level_formatter(
                "WARN", msg_format
            ),
            logging.ERROR: self._create_log_level_formatter(
                "ERROR", msg_format
            ),
            logging.CRITICAL: self._create_log_level_formatter(
                "CRITICAL", msg_format
            ),
        }

    def _create_log_level_formatter(self, symbol, msg_format):
        # pylint: disable=C0209
        format_str = "{timestamp} [{level}] {msg_format}".format(
            timestamp="%(asctime)s",
            level=symbol,
            msg_format=msg_format
        )
        return logging.Formatter(
            format_str,
            datefmt=FATHOM_LOG_FORMAT_TIMESTAMP
        )

    def format(self, record):
        formatter = self.log_level_formatters.get(record.levelno)
        assert formatter is not None
        return formatter.format(record)


class Logger(BaseLogger):
    """Fathom server application logger."""

    @staticmethod
    def get() -> BaseLogger:
        """Obtains a Fathom server application logger.

        Returns:
            Logger: A `Logger` object for the Fathom server.
        """
        return BaseLogger.get_logger(FATHOM_SERVER_LOGGER_NAME)

    @staticmethod
    def server_log_file_directory() -> File:
        """Gets the directory where the server log files are stored.

        Creates the directory if it does not already exist.

        Returns:
            File: A `File` object representing the directory.

        Raises:
            FileIOException: If the logs directory cannot be created.
        """
        ctx = ApplicationContext.instance()
        work_dir = ctx.get_working_directory()
        log_dir = work_dir / FATHOM_SERVER_LOGS_DIRECTORY_NAME
        if not log_dir.exists():
            log_dir.create_directory()

        return log_dir


class ServerLogger:
    """A logger for the CherryPy HTTP server engine."""

    _LOG_CONTEXT: Final = "SERVER"

    @staticmethod
    def get() -> "ServerLogger":
        """Obtains a Fathom server engine logger.

        Returns:
            ServerLogger: A `ServerLogger` object.
        """
        return ServerLogger()

    def log(self, message: str):
        """Logs a message to the HTTP server engine logs."""
        cherrypy.log(message, ServerLogger._LOG_CONTEXT)
