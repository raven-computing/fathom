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
"""CLI command handling."""

from abc import ABC, abstractmethod

from raven.fathom.client.logging import Logger
from raven.fathom.client.exceptions import InvalidConfigurationException
from raven.fathom.client.cli.arguments import ArgumentsCLI
from raven.fathom.client.cli.status import ExitStatus


LOG = Logger.get()


class Command(ABC):
    """Abstract base class for all CLI commands.

    Attributes:
        args (ArgumentsCLI): The `ArgumentsCLI` object used by the
            underlying CLI application.
        name (str): The name of the command, as a str.
    """

    def __init__(self, args: ArgumentsCLI):
        self.args = args
        self.name = args.command

    @abstractmethod
    def execute(self) -> ExitStatus:
        """Executes this command.
        
        Returns:
            ExitStatus: The exit status of the command, convertible to an int.
        """

    def cancel(self):
        """Lifecycle hook for command cancellation.

        This method is called when the command execution is interrupted,
        for example, by a user pressing Ctrl+C. Concrete commands may override
        this method to implement custom cancellation logic. It is not called in
        case of an encountered exception during command execution.
        An implementation must not raise any exceptions.
        The default implementation does nothing.
        """


def run(command: Command) -> ExitStatus:
    """Runs the given Command.

    Args:
        command: The concrete `Command` to run.

    Returns:
        ExitStatus: The exit status of the command, convertible to an `int`.
    """
    if command is None:
        LOG.e("No command provided")
        return ExitStatus.NO_COMMAND_PROVIDED

    try:
        exit_status = command.execute()
        if not isinstance(exit_status, ExitStatus):
            LOG.e(
                "Command %s returned invalid exit status. "
                "Expected value of type ExitStatus but found %s",
                command,
                type(exit_status)
            )
            exit_status = ExitStatus.INTERNAL_ERROR

        return exit_status
    except KeyboardInterrupt:
        LOG.i("Cancelling...")
        command.cancel()
        return ExitStatus.CANCELLED
    except InvalidConfigurationException as ex:
        LOG.e(str(ex))
        return ExitStatus.CONFIGURATION_ERROR
    except Exception as ex:  # pylint: disable=broad-exception-caught
        LOG.e(
            "An error occurred while executing command '%s'",
            command.name
        )
        LOG.e(str(ex))
        return ExitStatus.INTERNAL_ERROR
