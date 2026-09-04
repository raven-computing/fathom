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

from raven.fathom.base.decorators import noexcept


@dataclass(frozen=True)
class ArgumentsCLI:
    """Holds the parsed command line arguments provided by a CLI user."""

    verbose: bool = False

    debug: bool = False

    quiet: bool = False

    user: str = ""

    password: str = ""

    server: str = ""

    command: str = ""

    manage_subject: str = ""

    manage_command: str = ""

    setup_subject: str = ""

    managed_user_identifier: str = ""

    managed_user_name: str = ""

    setup_user_identifier: str = ""

    project_directory: str = ""


@noexcept
def parse_args(argv: list[str]) -> ArgumentsCLI:
    """Parses the arguments passed to the Fathom client program.

    Args:
        argv (list): The arguments vector.

    Returns:
        ArgumentsCLI: The processed command line arguments,
            as an `ArgumentsCLI` object.
    """
    parser = argparse.ArgumentParser(
        allow_abbrev=False,
        prog="fathom",
        description="Interact with a Fathom server.",
        epilog="Copyright (C) 2026 Raven Computing",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        default=ArgumentsCLI.verbose,
        help="Turn on verbose output."
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        default=ArgumentsCLI.debug,
        help="Turn on debug logging."
    )

    parser.add_argument(
        "--quiet",
        action="store_true",
        default=ArgumentsCLI.quiet,
        help="Turn off all output except errors."
    )

    parser.add_argument(
        "--user",
        action="store",
        default=ArgumentsCLI.user,
        help="The username to use for authentication."
    )

    parser.add_argument(
        "--password",
        action="store",
        default=ArgumentsCLI.password,
        help="The password to use for authentication."
    )

    parser.add_argument(
        "--server",
        action="store",
        default=ArgumentsCLI.server,
        help="The URL of the Fathom server to connect to."
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
        metavar="<COMMAND>",
    )

    deploy = subparsers.add_parser(
        "deploy",
        help="Deploy project documentation resources."
    )

    deploy.add_argument(
        "--project-directory",
        action="store",
        default=ArgumentsCLI.project_directory,
        help="The source root directory of the project to deploy."
    )

    manage = subparsers.add_parser(
        "manage",
        help="Manage server-side Fathom resources."
    )
    manage_subparsers = manage.add_subparsers(
        dest="manage_subject",
        required=True,
        metavar="<SUBJECT>",
    )

    manage_user = manage_subparsers.add_parser(
        "user",
        help="Manage dedicated application users on a Fathom server."
    )
    manage_user_subparsers = manage_user.add_subparsers(
        dest="manage_command",
        required=True,
        metavar="<ACTION>",
    )

    manage_user_create = manage_user_subparsers.add_parser(
        "create",
        help="Create a regular application user on the server."
    )
    manage_user_create.add_argument(
        "managed_user_identifier",
        metavar="<IDENTIFIER>",
        help="The unique identifier of the user to create."
    )
    manage_user_create.add_argument(
        "--name",
        default="",
        dest="managed_user_name",
        metavar="<NAME>",
        help="The display name of the user to create."
    )

    manage_user_subparsers.add_parser(
        "list",
        help="List dedicated application users on the server."
    )

    manage_user_delete = manage_user_subparsers.add_parser(
        "delete",
        help="Delete a dedicated application user on the server."
    )
    manage_user_delete.add_argument(
        "managed_user_identifier",
        metavar="<IDENTIFIER>",
        help="The unique identifier of the user to delete."
    )

    setup = subparsers.add_parser(
        "setup",
        help="Perform setup actions for the Fathom client."
    )
    setup_subparsers = setup.add_subparsers(
        dest="setup_subject",
        required=True,
        metavar="<SUBJECT>",
    )

    setup_user = setup_subparsers.add_parser(
        "user",
        help="Initialize an onboarding user account on a Fathom server."
    )
    setup_user.add_argument(
        "setup_user_identifier",
        nargs="?",
        default="",
        metavar="<IDENTIFIER>",
        help="The unique identifier of the user to initialize."
    )

    args = parser.parse_args(argv[1:])
    return ArgumentsCLI(
        verbose=args.verbose,
        debug=args.debug,
        quiet=args.quiet,
        user=args.user,
        password=args.password,
        server=args.server,
        command=args.command,
        manage_subject=getattr(args, "manage_subject", ""),
        manage_command=getattr(args, "manage_command", ""),
        setup_subject=getattr(args, "setup_subject", ""),
        managed_user_identifier=getattr(
            args, "managed_user_identifier", ""
        ),
        managed_user_name=getattr(args, "managed_user_name", ""),
        setup_user_identifier=getattr(args, "setup_user_identifier", ""),
        project_directory=getattr(args, "project_directory", "")
    )
