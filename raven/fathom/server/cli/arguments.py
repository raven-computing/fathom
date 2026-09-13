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
"""Command line argument handling."""

import argparse

from dataclasses import dataclass
from typing import Optional
from multiprocessing.synchronize import Event

from raven.fathom.server.defaults import DEFAULT_SERVER_PORT


def port_type(arg: str) -> int:
    """Validates and converts the argument for the port number."""
    port = int(arg)
    if port < 1 or port > 65535:
        raise argparse.ArgumentTypeError("Port must be between 1 and 65535")

    return port


@dataclass(frozen=True)
class AppArgs:
    """Holds the parsed command line arguments."""

    verbose: bool = False

    debug: bool = False

    port: Optional[int] = None

    working_directory: str = ""

    create_default_config: bool = False

    command: str = ""

    user_command: str = ""

    project_command: str = ""

    user_identifier: str = ""

    user_name: str = ""

    user_is_admin: bool = False

    project_identifier: str = ""

    project_name: str = ""

    project_description: str = ""

    ready_event: Optional[Event] = None


def parse_args(argv: list[str]) -> AppArgs:
    """Parses the arguments passed to the Fathom server.

    Args:
        argv (list): The arguments vector.

    Returns:
        AppArgs: The processed command line arguments.
    """
    last_arg = argv[len(argv)-1] if len(argv) > 0 else None
    event = None
    if isinstance(last_arg, Event):
        event = last_arg
        argv = argv[:-1]

    parser = argparse.ArgumentParser(
        allow_abbrev=False,
        prog="fathom-server",
        description="The Fathom server application.",
        epilog="Copyright (C) 2026 Raven Computing",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        default=AppArgs.verbose,
        help="Turn on verbose logging."
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        default=AppArgs.debug,
        help="Turn on debug logging."
    )

    parser.add_argument(
        "--port",
        metavar="<PORT>",
        type=port_type,
        default=None, # Need to be able to check if specified or not by user
        help="The port number on which the server will listen. "
            f"The default port is {DEFAULT_SERVER_PORT}."
    )

    parser.add_argument(
        "--working-directory",
        metavar="<PATH>",
        default=AppArgs.working_directory,
        help="The absolute path to the directory of the server application "
             "where server-specific files are located."
    )

    parser.add_argument(
        "--create-default-config",
        action="store_true",
        default=AppArgs.create_default_config,
        help="Create the server configuration file with default values "
             "if the file does not alreday exist at startup."
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=False,
        metavar="<COMMAND>",
    )

    subparsers.add_parser(
        "setup",
        help="Perform initial setup work for the server application."
    )

    user_parser = subparsers.add_parser(
        "user",
        help="Manage dedicated application users."
    )
    user_subparsers = user_parser.add_subparsers(
        dest="user_command",
        required=True,
        metavar="<USER_COMMAND>",
    )

    user_create = user_subparsers.add_parser(
        "create",
        help="Create a user in the local Fathom datastore."
    )
    user_create.add_argument(
        "identifier",
        metavar="<IDENTIFIER>",
        help="The unique identifier of the user to create."
    )
    user_create.add_argument(
        "--name",
        default="",
        metavar="<NAME>",
        help="The human-readable display name of the user."
    )
    user_create.add_argument(
        "--admin",
        action="store_true",
        default=False,
        help="Create the user with administrator permissions."
    )

    user_subparsers.add_parser(
        "list",
        help="List users from the local Fathom datastore."
    )

    user_delete = user_subparsers.add_parser(
        "delete",
        help="Delete a user from the local Fathom datastore."
    )
    user_delete.add_argument(
        "identifier",
        metavar="<IDENTIFIER>",
        help="The unique identifier of the user to delete."
    )

    project_parser = subparsers.add_parser(
        "project",
        help="Manage deployable projects."
    )
    project_subparsers = project_parser.add_subparsers(
        dest="project_command",
        required=True,
        metavar="<PROJECT_COMMAND>",
    )

    project_create = project_subparsers.add_parser(
        "create",
        help="Create a project in the local Fathom datastore."
    )
    project_create.add_argument(
        "identifier",
        metavar="<IDENTIFIER>",
        help="The unique identifier of the project to create."
    )
    project_create.add_argument(
        "--name",
        default="",
        metavar="<NAME>",
        help="The human-readable display name of the project."
    )
    project_create.add_argument(
        "--description",
        default="",
        metavar="<DESCRIPTION>",
        help="The human-readable description of the project."
    )

    project_subparsers.add_parser(
        "list",
        help="List projects from the local Fathom datastore."
    )

    project_delete = project_subparsers.add_parser(
        "delete",
        help="Delete a project from the local Fathom datastore."
    )
    project_delete.add_argument(
        "identifier",
        metavar="<IDENTIFIER>",
        help="The unique identifier of the project to delete."
    )

    args = parser.parse_args(argv[1:])
    return AppArgs(
        verbose=args.verbose,
        debug=args.debug,
        port=args.port,
        working_directory=args.working_directory,
        create_default_config=args.create_default_config,
        command=args.command,
        user_command=getattr(args, "user_command", ""),
        project_command=getattr(args, "project_command", ""),
        user_identifier=getattr(args, "identifier", ""),
        user_name=getattr(args, "name", ""),
        user_is_admin=getattr(args, "admin", False),
        project_identifier=getattr(args, "identifier", ""),
        project_name=getattr(args, "name", ""),
        project_description=getattr(args, "description", ""),
        ready_event=event,
    )
