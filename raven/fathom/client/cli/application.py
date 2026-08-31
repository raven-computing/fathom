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
"""Fathom client CLI entry point."""

import sys

from typing import Optional

from raven.fathom.base import ApplicationContext
from raven.fathom.client.logging import setup_cli_logger, setup_file_logger
from raven.fathom.client.logging import shutdown_loggers
from raven.fathom.client.context import determine_client_application_mode
from raven.fathom.client.context import determine_client_working_directory
from raven.fathom.client.config import UserConfiguration, ConfigurationManager
from raven.fathom.client.cli.arguments import ArgumentsCLI, parse_args
from raven.fathom.client.cli.command import run
from raven.fathom.client.cli.registry import command_with_args
from raven.fathom.client.cli.status import ExitStatus


def _setup_client(args: ArgumentsCLI):
    setup_cli_logger(args)
    cm = ConfigurationManager()
    cm.load_configs(args)
    config = cm.get_user_config()
    if config[UserConfiguration.USER.LOGGING_ENABLED]:
        setup_file_logger(args)


def main(argv: Optional[list[str]] = None) -> ExitStatus:
    """Main function of the Fathom client CLI application.

    Args:
        argv (list): The list of str program arguments. If left as `None`,
            then the arguments are taken from `sys.argv`.

    Returns:
        ExitStatus: The exit status of the program.
    """
    if argv is None:
        argv = sys.argv

    args = parse_args(argv)

    app_mode = determine_client_application_mode()
    working_directory = determine_client_working_directory(app_mode)
    ctx = ApplicationContext.create_instance()
    with ctx.initialize(app_mode, working_directory):
        try:
            _setup_client(args)
            return run(command_with_args(args))
        except Exception as ex:  # pylint: disable=broad-exception-caught
            print("Failed to setup Fathom client:", file=sys.stderr)
            print(str(ex), file=sys.stderr)
            return ExitStatus.INTERNAL_ERROR
        finally:
            shutdown_loggers()


if __name__ == "__main__":
    sys.exit(int(main(sys.argv)))
