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
"""CLI command registry."""

from raven.fathom.server.cli.arguments import AppArgs
from raven.fathom.server.cli.arguments import AppCommand
from raven.fathom.server.cli.command import ServerCommand
from raven.fathom.server.cli.reset import ResetSharedSecretCommand
from raven.fathom.server.cli.reset import ResetUserCommand
from raven.fathom.server.cli.serve import ServeCommand
from raven.fathom.server.cli.setup import SetupCommand
from raven.fathom.server.core.logging import Logger


LOG = Logger.get()


def create_command(args: AppArgs) -> ServerCommand:
    """Creates a concrete server command from parsed CLI arguments.

    Args:
        args (AppArgs): The parsed command-line arguments.

    Returns:
        ServerCommand: A concrete `ServerCommand` instance that can
            be executed. Returns a command that starts and runs the server
            if no command was specified in the given arguments.

    Raises:
        ValueError: If the command name is invalid.
    """
    LOG.d("Creating Command object from CLI command arg '%s'", args.command)
    if args.command in (AppCommand.SERVE, AppCommand.UNSPECIFIED):
        return ServeCommand(args)

    if args.command == AppCommand.SETUP:
        return SetupCommand(args)

    if args.command == AppCommand.RESET:
        if args.reset_subject == AppCommand.USER:
            return ResetUserCommand(args)
        if args.reset_subject == AppCommand.SHARED_SECRET:
            return ResetSharedSecretCommand(args)
        raise ValueError(f"Invalid reset subject '{args.reset_subject}'")

    raise ValueError(f"Invalid command '{args.command}'")
