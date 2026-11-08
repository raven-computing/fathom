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
"""Signal handling for the Fathom server application."""

import signal as _signal

from raven.fathom.base import log_stdout
from raven.fathom.server.cli.command import ServerCommand
from raven.fathom.server.core.logging import Logger


LOG = Logger.get()

_HANDLED_SIGNALS = ("SIGINT", "SIGTERM")


class CommandSignalHandler:
    """Context manager that intercepts OS signals for a server command.

    Installs SIGINT and SIGTERM handlers that invoke `command.cancel()`
    on entry and restores the previously registered handlers on exit.
    """

    def __init__(self, command: ServerCommand):
        self._command = command
        self._previous_handlers: dict = {}

    def __enter__(self) -> "CommandSignalHandler":
        for signal_name in _HANDLED_SIGNALS:
            sig = getattr(_signal, signal_name, None)
            if sig is not None:
                LOG.d("Listening for %s", signal_name)
                previous_handler = _signal.getsignal(sig)
                LOG.d(
                    "Previous signal handler for %s: %s",
                    signal_name,
                    previous_handler,
                )
                self._previous_handlers[sig] = previous_handler
                _signal.signal(sig, self._handle_pyrt_sig)

        return self

    def __exit__(self, ex_type, ex_value, ex_trace):
        for sig, handler in self._previous_handlers.items():
            LOG.d("Reinstating handler for signal %s", sig)
            _signal.signal(sig, handler)

        self._previous_handlers.clear()

    def _handle_pyrt_sig(self, signum, _frame) -> None:
        LOG.d("Received signal %s", signum)
        log_stdout("")
        LOG.i("Cancelling...")
        LOG.d(
            "Invoking command cancellation for %s due to trapped signal",
            self._command,
        )
        self._command.cancel()
