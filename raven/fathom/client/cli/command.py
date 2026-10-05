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
"""Client CLI command handling."""

from raven.fathom.base import Command
from raven.fathom.client.logging import Logger
from raven.fathom.client.exceptions import InvalidConfigurationException
from raven.fathom.client.cli.arguments import ArgumentsCLI
from raven.fathom.client.cli.status import ExitStatus


LOG = Logger.get()


class ClientCommand(Command):
    """Base class for all client CLI commands.

    Attributes:
        args (ArgumentsCLI): The `ArgumentsCLI` object used by
            the underlying CLI application.
    """

    def __init__(self, args: ArgumentsCLI):
        self.args = args
        super().__init__(args.command)


def run(command: ClientCommand | None) -> ExitStatus:
    """Runs the given Command.

    Args:
        command: The concrete `Command` to run, or `None` if no command
            was specified on the command-line.

    Returns:
        ExitStatus: The exit status of the command, convertible to an `int`.
    """
    if command is None:
        LOG.e("No command specified")
        return ExitStatus.NO_COMMAND_PROVIDED

    exit_status = None
    try:
        exit_status = command.execute()
        return ExitStatus(exit_status)
    except ValueError:
        LOG.e(
            "Command %s returned invalid exit status. "
            "Expected value of ExitStatus but found %s",
            command,
            exit_status
        )
        return ExitStatus.INTERNAL_ERROR
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
        LOG.d("Caught %s", type(ex).__name__, exc_info=True)
        return ExitStatus.INTERNAL_ERROR
