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
"""Fathom logging utilities."""

import sys
import logging
import threading

from typing import Union, overload
from enum import IntEnum

from raven.fathom.base import File
from raven.fathom.base.decorators import singleton


class LogLevel(IntEnum):
    """Enumeration of supported logging levels.

    The ordering is with respect to granularity, from least to most granular.
    """

    CRITICAL = 1

    ERROR = 2

    WARNING = 3

    INFO = 4

    VERBOSE = 5

    DEBUG = 6


class LogHandlerCLI(logging.StreamHandler):
    """A `logging.StreamHandler` used for CLI applications."""

    def __init__(self):
        super().__init__(sys.stdout)


class LogHandlerFile(logging.FileHandler):
    """A `logging.FileHandler` used for keeping log files."""

    def __init__(self, file: File):
        super().__init__(filename=str(file.path), mode="a", encoding="UTF-8")


class LogFormatterCLI(logging.Formatter):
    """A `logging.Formatter` used for CLI applications."""

    COLOR_RED = "\033[0;31m"

    COLOR_GREEN = "\033[1;32m"

    COLOR_BLUE = "\033[1;34m"

    COLOR_CYAN = "\033[1;36m"

    COLOR_ORANGE = "\033[1;33m"

    COLOR_NC = "\033[0m"

    INPUT_PROMPT = f"[{COLOR_CYAN}INPUT{COLOR_NC}]"

    MSG_FORMAT = "%(message)s"

    def __init__(
        self,
        include_timestamp: bool = False,
        use_colours: bool = True,
        prefix: str = ""
    ):
        super().__init__()
        self._include_timestamp = include_timestamp
        msg_format = LogFormatterCLI.MSG_FORMAT
        self.log_level_formatters = {
            logging.DEBUG: self._create_log_level_formatter(
                "DEBUG",
                use_colours and LogFormatterCLI.COLOR_BLUE,
                prefix,
                msg_format,
            ),
            logging.INFO: self._create_log_level_formatter(
                "INFO",
                use_colours and LogFormatterCLI.COLOR_BLUE,
                prefix,
                msg_format,
            ),
            logging.WARNING: self._create_log_level_formatter(
                "WARN",
                use_colours and LogFormatterCLI.COLOR_ORANGE,
                prefix,
                msg_format,
            ),
            logging.ERROR: self._create_log_level_formatter(
                "ERROR",
                use_colours and LogFormatterCLI.COLOR_RED,
                prefix,
                msg_format,
            ),
            logging.CRITICAL: self._create_log_level_formatter(
                "CRITICAL",
                use_colours and LogFormatterCLI.COLOR_RED,
                prefix,
                msg_format,
            ),
        }

    def _create_log_level_formatter(self, symbol, color, prefix, msg_format):
        # pylint: disable=consider-using-f-string
        frmt = "{timestamp}[{color}{level}{nc}] {prefix}{msg_format}".format(
            timestamp="%(asctime)s " if self._include_timestamp else "",
            color=color or "",
            level=symbol,
            nc=LogFormatterCLI.COLOR_NC if color else "",
            prefix=f"{prefix} " if prefix else "",
            msg_format=msg_format
        )
        return logging.Formatter(frmt, datefmt="%Y-%m-%dT%H:%M:%S")

    def format(self, record):
        formatter = self.log_level_formatters.get(record.levelno)
        assert formatter is not None
        return formatter.format(record)

    @staticmethod
    def format_message_info(message: str) -> str:
        """Formats a log message determined for an input prompt."""
        return f"{LogFormatterCLI.INPUT_PROMPT} {message}"


_LOG_LEVEL_MAP = {
    LogLevel.CRITICAL: logging.CRITICAL,
    LogLevel.ERROR: logging.ERROR,
    LogLevel.WARNING: logging.WARNING,
    LogLevel.INFO: logging.INFO,
    LogLevel.VERBOSE: logging.INFO,  # Verbose is treated as INFO
    LogLevel.DEBUG: logging.DEBUG,
}


@singleton
class LogManager:
    """Global application-wide management of loggers and their configurations.

    Should be used by applications during their initialization phase to
    set up loggers, handlers, and formatters. Then when the application
    shuts down, it should call `shutdown_loggers()` to ensure proper cleanup
    of logging resources.
    """

    def __init__(self):
        self._loggers: dict[str, Logger] = dict()
        self._handlers: list[logging.Handler] = []
        self._lock = threading.RLock()

    def get_log_level(self, name: str) -> LogLevel:
        """Returns the log level for a given logger name.

        Args:
            name (str): The name of the logger.

        Returns:
            LogLevel: The log level of the logger.
        """
        logger = self._loggers.get(name)
        if logger is None:
            raise ValueError(f"Logger '{name}' is not set up")

        return logger.level

    def set_log_level(self, name: str, level: LogLevel):
        """Sets the log level for the logger with the given name.

        Args:
            name (str): The name of the logger.
            level (LogLevel): The log level to set.
        """
        std_log_level = self._map_log_level(level)
        std_logger = logging.getLogger(name)
        std_logger.setLevel(std_log_level)

    def get_logger(self, name: str) -> "Logger":
        """Obtains a `Logger` object.

        Args:
            name (str): The name of the logger to obtain.

        Returns:
            Logger: A `Logger` object.
        """
        with self._lock:
            logger = self._loggers.get(name)
            if logger is None:
                std_logger = logging.getLogger(name)
                log_level = LogLevel.INFO
                std_logger.disabled = True
                logger = Logger(std_logger, log_level)
                self._loggers[name] = logger
                return logger

            return logger

    def setup_logger(
        self,
        name: str,
        level: LogLevel,
        handlers: Union[logging.Handler, list[logging.Handler]],
        formatters: Union[logging.Formatter, list[logging.Formatter]]
    ):
        """Sets up a logger with the given name and log level.

        Args:
            name (str): The name of the logger to set up.
            level (LogLevel): The log level for the logger.
            handlers (list): The handler(s) to attach to the logger.
            formatters (list): The formatter(s) to use for the handler(s).
        """
        with self._lock:
            if not isinstance(handlers, list):
                handlers = [handlers]

            if not isinstance(formatters, list):
                formatters = [formatters]

            if len(handlers) != len(formatters):
                raise ValueError(
                    "Number of handlers must match number of formatters"
                )

            logger = self.get_logger(name)
            std_logger = logging.getLogger(name)
            std_logger.disabled = False
            for handler, formatter in zip(handlers, formatters):
                handler.setLevel(self._map_log_level(level))
                handler.setFormatter(formatter)
                std_logger.addHandler(handler)

            logger.level = level
            self._loggers[name] = logger
            self._handlers.extend(handlers)

    def shutdown_loggers(self):
        """Executes shutdown procedures for the logging system.

        Should be called by applications before exiting to ensure
        proper cleanup of logging resources.
        """
        with self._lock:
            for handler in self._handlers:
                handler.close()

            logging.shutdown()

    def _map_log_level(self, level):
        return _LOG_LEVEL_MAP.get(level, logging.INFO)


class Logger:
    """An application logger.

    The central API for logging messages in the application. Usually,
    application code can simply import this class, obtain a logger
    via `Logger.get_logger()` and store it in the global scope of the
    underlying module, and then use the logging methods to log messages
    at various levels.
    """

    def __init__(self, logger: logging.Logger, level: LogLevel):
        self._log = logger
        self._level = level

    @property
    def level(self) -> LogLevel:
        """The log level of the logger, as a `LogLevel`."""
        return self._level

    @level.setter
    def level(self, value: LogLevel):
        """Sets the log level of the logger.

        Args:
            value (LogLevel): The new log level to set.
        """
        LogManager().set_log_level(self._log.name, value)
        self._level = value

    def critical(self, message: str, *args, **kwargs):
        """Logs a message with level CRITICAL."""
        self._log.critical(message, *args, **kwargs)

    @overload
    def e(self, message: Exception, *args, **kwargs):
        ...
    @overload
    def e(self, message: str, *args, **kwargs):
        ...
    def e(self, message, *args, **kwargs):
        """Logs a message with level ERROR."""
        self._log.error(
            message,
            *args,
            **kwargs,
        )

    def w(self, message: str, *args, **kwargs):
        """Logs a message with level WARNING."""
        self._log.warning(message, *args, **kwargs)

    def i(self, message: str, *args, **kwargs):
        """Logs a message with level INFO."""
        self._log.info(message, *args, **kwargs)

    def v(self, message: str, *args, **kwargs):
        """Logs a message with level VERBOSE."""
        if self._level >= LogLevel.VERBOSE:
            self._log.info(message, *args, **kwargs)

    def d(self, message: str, *args, **kwargs):
        """Logs a message with level DEBUG."""
        self._log.debug(message, *args, **kwargs)

    def log(self, level: LogLevel, message: str, *args, **kwargs):
        """Logs a message with the specified log level.

        Args:
            level (LogLevel): The log level to use.
            message (str): The message to log.
        """
        self._log.log(
            _LOG_LEVEL_MAP.get(level, logging.INFO),
            message,
            *args, **kwargs
        )

    @staticmethod
    def get_logger(name: str) -> "Logger":
        """Obtains logger object.

        Args:
            name (str): The name of the logger to obtain.

        Returns:
            Logger: A `Logger` instance.
        """
        return LogManager().get_logger(name)
