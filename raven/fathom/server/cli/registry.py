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
from raven.fathom.server.cli.command import ServerCommand
from raven.fathom.server.cli.project import ProjectCreateCommand
from raven.fathom.server.cli.project import ProjectDeleteCommand
from raven.fathom.server.cli.project import ProjectListCommand
from raven.fathom.server.cli.run import RunServerCommand
from raven.fathom.server.cli.setup import SetupCommand
from raven.fathom.server.cli.user import UserCreateCommand
from raven.fathom.server.cli.user import UserDeleteCommand
from raven.fathom.server.cli.user import UserListCommand


def command_with_args(args: AppArgs) -> ServerCommand:
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
    if not args.command:
        return RunServerCommand(args)

    if args.command == "setup":
        return SetupCommand(args)

    if args.command == "user":
        if args.user_command == "create":
            return UserCreateCommand(args)
        if args.user_command == "list":
            return UserListCommand(args)
        if args.user_command == "delete":
            return UserDeleteCommand(args)

        raise ValueError(f"Invalid user command '{args.user_command}'")

    if args.command == "project":
        if args.project_command == "create":
            return ProjectCreateCommand(args)
        if args.project_command == "list":
            return ProjectListCommand(args)
        if args.project_command == "delete":
            return ProjectDeleteCommand(args)

        raise ValueError(f"Invalid project command '{args.project_command}'")

    raise ValueError(f"Invalid command '{args.command}'")
