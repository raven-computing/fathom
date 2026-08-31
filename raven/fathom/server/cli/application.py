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
"""Fathom server main entry point."""

import sys

from typing import Optional

from raven.fathom.base import ApplicationContext
from raven.fathom.base import File

from raven.fathom.server.logging import setup_server_logging, log_stderr
from raven.fathom.server.logging import shutdown_loggers
from raven.fathom.server.context import determine_server_application_mode
from raven.fathom.server.context import determine_server_working_directory
from raven.fathom.server.cli.arguments import parse_args
from raven.fathom.server.cli.status import ExitStatus
from raven.fathom.server.main import run


def main(argv: Optional[list[str]] = None) -> ExitStatus:
    """Main function of the Fathom server application.

    Args:
        argv (list): The list of str program arguments. If left as `None`,
            then the arguments are taken from `sys.argv`.

    Returns:
        ExitStatus: The exit status of the program.
    """
    if argv is None:
        argv = sys.argv

    args = parse_args(argv)
    work_dir = None
    if args.working_directory:
        work_dir = File(args.working_directory)
        if not work_dir.path.is_absolute():
            log_stderr(
                "Error: The working directory must be an absolute path."
            )
            return ExitStatus.FAILURE

        if not work_dir.is_directory():
            log_stderr(
                f"Error: The working directory '{work_dir.path}' "
                "does not exist or is not a directory."
            )
            return ExitStatus.FAILURE

    app_mode = determine_server_application_mode()
    if work_dir is None:
        work_dir = determine_server_working_directory(app_mode)

    app_ctx = ApplicationContext.create_instance()
    with app_ctx.initialize(app_mode, work_dir):
        try:
            setup_server_logging(args)
            return ExitStatus(run(args))
        except Exception as ex:  # pylint: disable=broad-exception-caught
            log_stderr(f"Error: {ex}")
            return ExitStatus.FAILURE
        finally:
            shutdown_loggers()


if __name__ == "__main__":
    sys.exit(int(main(sys.argv)))
