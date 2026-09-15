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
from raven.fathom.base.context import APPLICATION_PROJECT_ID, APPLICATION_NAME


# pylint: disable=too-many-locals


@dataclass(frozen=True)
class ArgumentsCLI:
    """Holds the parsed command line arguments provided by a CLI user."""

    verbose: bool = False

    debug: bool = False

    quiet: bool = False

    version: bool = False

    version_short: bool = False

    user: str = ""

    password: str = ""

    server: str = ""

    command: str = ""

    manage_subject: str = ""

    manage_command: str = ""

    setup_subject: str = ""

    user_identifier: str = ""

    user_name: str = ""

    project_identifier: str = ""

    project_name: str = ""

    project_description: str = ""

    setup_user_identifier: str = ""

    project_directory: str = ""


class _VersionOptAction(argparse.Action):
    def __init__(self, option_strings, dest, **kwargs):
        super().__init__(option_strings, dest, nargs=0, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        namespace.version = True
        namespace.version_short = option_string == "-#"


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
        add_help=False,
        prog=APPLICATION_PROJECT_ID,
        description=f"Interact with a {APPLICATION_NAME} server.",
        usage='%(prog)s [options] <COMMAND> ...',
        epilog="[This version of the Fathom client is a Beta build]",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        default=ArgumentsCLI.debug,
        help="Turn on debug logging."
    )
    parser.add_argument(
        "--password",
        action="store",
        default=ArgumentsCLI.password,
        help="The password to use for authentication. If this option is used, "
             "the application will not prompt the user to enter a password on "
             "the command-line. If you intend to use this option in a "
             "non-development environment, it is recommended that you "
             "instruct your shell to not store the entered command in its "
             "history so that the password is not exposed. Consider passing "
             "the password via the FATHOM_CLIENT_PASSWORD environment "
             "variable instead."
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        default=ArgumentsCLI.quiet,
        help="Turn off all output except errors."
    )
    parser.add_argument(
        "--server",
        action="store",
        default=ArgumentsCLI.server,
        help=f"The URL of the {APPLICATION_NAME} server to connect to."
    )
    parser.add_argument(
        "--user",
        action="store",
        default=ArgumentsCLI.user,
        help="The username to use for authentication."
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=ArgumentsCLI.verbose,
        help="Turn on verbose output."
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=False,  # Missing command arg is handled by app code
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
        help="The path to the source root directory of the project to deploy."
    )

    manage = subparsers.add_parser(
        "manage",
        help=f"Manage server-side {APPLICATION_NAME} resources."
    )
    manage_subparsers = manage.add_subparsers(
        dest="manage_subject",
        required=True,
        metavar="<SUBJECT>",
    )

    manage_user = manage_subparsers.add_parser(
        "user",
        help="Manage dedicated application users "
            f"on a {APPLICATION_NAME} server."
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
        "user_identifier",
        metavar="<IDENTIFIER>",
        help="The unique identifier of the user to create."
    )
    manage_user_create.add_argument(
        "--name",
        default="",
        dest="user_name",
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
        "user_identifier",
        metavar="<IDENTIFIER>",
        help="The unique identifier of the user to delete."
    )

    manage_project = manage_subparsers.add_parser(
        "project",
        help=f"Manage deployable projects on a {APPLICATION_NAME} server."
    )
    manage_project_subparsers = manage_project.add_subparsers(
        dest="manage_command",
        required=True,
        metavar="<ACTION>",
    )

    manage_project_create = manage_project_subparsers.add_parser(
        "create",
        help="Create a deployable project on the server."
    )
    manage_project_create.add_argument(
        "project_identifier",
        metavar="<IDENTIFIER>",
        help="The unique identifier of the project to create."
    )
    manage_project_create.add_argument(
        "--name",
        default="",
        dest="project_name",
        metavar="<NAME>",
        help="The display name of the project to create."
    )
    manage_project_create.add_argument(
        "--description",
        default="",
        dest="project_description",
        metavar="<DESCRIPTION>",
        help="The description of the project to create."
    )

    manage_project_subparsers.add_parser(
        "list",
        help="List deployable projects on the server."
    )

    manage_project_delete = manage_project_subparsers.add_parser(
        "delete",
        help="Delete a deployable project on the server."
    )
    manage_project_delete.add_argument(
        "project_identifier",
        metavar="<IDENTIFIER>",
        help="The unique identifier of the project to delete."
    )

    setup = subparsers.add_parser(
        "setup",
        help=f"Perform setup actions for the {APPLICATION_NAME} client."
    )
    setup_subparsers = setup.add_subparsers(
        dest="setup_subject",
        required=True,
        metavar="<SUBJECT>",
    )

    setup_user = setup_subparsers.add_parser(
        "user",
        help="Initialize an onboarding user account "
            f"on a {APPLICATION_NAME} server."
    )
    setup_user.add_argument(
        "setup_user_identifier",
        nargs="?",
        default="",
        metavar="<IDENTIFIER>",
        help="The unique identifier of the user to initialize."
    )
    parser.add_argument(
        "-#",
        "--version",
        action=_VersionOptAction,
        default=ArgumentsCLI.version,
        help="Show program version information and then exit.",
    )
    parser.add_argument(
        "-?",
        "--help",
        action="help",
        default=argparse.SUPPRESS,
        help="Show this help message and then exit.",
    )

    args = parser.parse_args(argv[1:])
    return ArgumentsCLI(
        verbose=args.verbose,
        debug=args.debug,
        quiet=args.quiet,
        version=bool(getattr(args, "version", "")),
        version_short=bool(getattr(args, "version_short", "")),
        user=args.user,
        password=args.password,
        server=args.server,
        command=args.command,
        manage_subject=getattr(args, "manage_subject", ""),
        manage_command=getattr(args, "manage_command", ""),
        setup_subject=getattr(args, "setup_subject", ""),
        user_identifier=getattr(args, "user_identifier", ""),
        user_name=getattr(args, "user_name", ""),
        project_identifier=getattr(args, "project_identifier", ""),
        project_name=getattr(args, "project_name", ""),
        project_description=getattr(args, "project_description", ""),
        setup_user_identifier=getattr(args, "setup_user_identifier", ""),
        project_directory=getattr(args, "project_directory", "")
    )
