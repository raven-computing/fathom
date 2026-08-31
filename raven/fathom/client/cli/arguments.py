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

    args = parser.parse_args(argv[1:])
    return ArgumentsCLI(
        verbose=args.verbose,
        debug=args.debug,
        quiet=args.quiet,
        user=args.user,
        password=args.password,
        server=args.server,
        command=args.command,
        project_directory=args.project_directory
    )
