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

from enum import StrEnum
from dataclasses import dataclass
from typing import Optional
from multiprocessing.synchronize import Event

from raven.fathom.base import ArgumentParser
from raven.fathom.base.context import APPLICATION_PROJECT_ID, APPLICATION_NAME
from raven.fathom.server.net.defaults import DEFAULT_SERVER_PORT

# pylint: disable=too-many-locals


def port_type(arg: str) -> int:
    """Validates and converts the argument for the port number."""
    port = int(arg)
    if port < 1 or port > 65535:
        raise argparse.ArgumentTypeError("Port must be between 1 and 65535")

    return port


class AppCommand(StrEnum):
    """Supported server CLI command names and subcommand names."""

    UNSPECIFIED = ""

    SERVE = "serve"

    SETUP = "setup"

    RESET = "reset"

    USER = "user"

    SHARED_SECRET = "shared-secret"


@dataclass(frozen=True)
class AppArgs:
    """Holds the parsed command line arguments."""

    verbose: bool = False

    debug: bool = False

    version: bool = False

    version_short: bool = False

    port: Optional[int] = None

    working_directory: str = ""

    config_file: str = ""

    create_default_config: bool = False

    command: AppCommand = AppCommand.SERVE

    reset_subject: AppCommand = AppCommand.UNSPECIFIED

    reset_user_identifier: str = ""

    ready_event: Optional[Event] = None

    shutdown_event: Optional[Event] = None


def parse_args(argv: list[str]) -> AppArgs:
    """Parses the arguments passed to the Fathom server.

    Args:
        argv (list): The arguments vector.

    Returns:
        AppArgs: The processed command line arguments.
    """
    last_arg = argv[len(argv)-1] if len(argv) > 0 else None
    ready_event = None
    if isinstance(last_arg, Event):
        ready_event = last_arg
        argv = argv[:-1]

    last_arg = argv[len(argv)-1] if len(argv) > 0 else None
    shutdown_event = None
    if isinstance(last_arg, Event):
        shutdown_event = last_arg
        argv = argv[:-1]

    parser = ArgumentParser(
        allow_abbrev=False,
        prog=f"{APPLICATION_PROJECT_ID}-server",
        description=f"Starts the {APPLICATION_NAME} server to serve incoming "
                     "client requests. Use one of the available commands to "
                     "setup and manage the server application and its "
                     "resources.",
        usage="%(prog)s [options] [command] ...",
        epilog="[This version of the Fathom server is a Beta build]",
    )

    parser.add_argument(
        "--config-file",
        metavar="<PATH>",
        default=AppArgs.config_file,
        help="The absolute path to the server configuration file. "
             "When omitted, known configuration names are searched "
             "in the server working directory."
    )
    parser.add_argument(
        "--create-default-config",
        action="store_true",
        default=AppArgs.create_default_config,
        help="Create the server configuration file with default values "
             "if the file does not already exist at startup."
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
        "--verbose",
        action="store_true",
        default=AppArgs.verbose,
        help="Turn on verbose logging."
    )
    parser.add_argument(
        "--working-directory",
        metavar="<PATH>",
        default=AppArgs.working_directory,
        help="The absolute path to the directory of the server application "
             "where server-specific files are located."
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=False,
        metavar="[command]",
    )
    subparsers.add_parser(
        str(AppCommand.SERVE),
        help="Starts the server to serve incoming client requests. "
             "This is the default if no command is explicitly specified.",
    )
    subparsers.add_parser(
        str(AppCommand.SETUP),
        help="Perform initial setup work for the server application. "
             "This should be done once after installation. "
             "This step is interactive."
    )

    reset_parser = subparsers.add_parser(
        str(AppCommand.RESET),
        help="Perform a local administrative reset operation. "
             "Requires authentication as the system user."
    )
    reset_subparsers = reset_parser.add_subparsers(
        dest="reset_subject",
        required=True,
        metavar="<SUBJECT>",
    )

    reset_user = reset_subparsers.add_parser(
        str(AppCommand.USER),
        help="Reset a user's credentials. The user will be placed in RESET "
             "state and must re-establish their password via the client "
             "sign-up procedure using the current shared secret."
    )
    reset_user.add_argument(
        "identifier",
        metavar="<IDENTIFIER>",
        help="The unique identifier of the user whose credentials to reset."
    )

    reset_subparsers.add_parser(
        str(AppCommand.SHARED_SECRET),
        help="Rotate the organisation's shared signup secret. "
             "Users who are currently in ONBOARDING or RESET state will "
             "need their credentials reset again to receive the new secret."
    )

    parser.add_version_argument()

    args = parser.parse_args(argv[1:])
    return AppArgs(
        verbose=args.verbose,
        debug=args.debug,
        version=bool(getattr(args, "version", "")),
        version_short=bool(getattr(args, "version_short", "")),
        port=args.port,
        working_directory=args.working_directory,
        config_file=args.config_file,
        create_default_config=args.create_default_config,
        command=(
            AppCommand.SERVE
            if args.command is None
            else AppCommand(args.command)
        ),
        reset_subject=AppCommand(
            getattr(args, "reset_subject", str(AppCommand.UNSPECIFIED))
        ),
        reset_user_identifier=getattr(args, "identifier", ""),
        ready_event=ready_event,
        shutdown_event=shutdown_event,
    )
