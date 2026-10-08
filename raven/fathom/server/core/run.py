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
"""Fathom server command execution entry point."""

from raven.fathom.base import ApplicationContext, ApplicationMode
from raven.fathom.server.cli.arguments import AppArgs, AppCommand
from raven.fathom.server.cli.registry import create_command
from raven.fathom.server.cli.status import ExitStatus
from raven.fathom.server.core.config import ConfigurationManager
from raven.fathom.server.core.logging import Logger
from raven.fathom.server.core.setup import require_server_setup
from raven.fathom.server.core.setup import setup_application


LOG = Logger.get()


def run_server(args: AppArgs) -> ExitStatus:
    """Runs a command of the Fathom server application.

    Args:
        args (AppArgs): The application arguments to be used.

    Returns:
        ExitStatus: The exit status code of the server.
    """
    app_mode = ApplicationContext.instance().get_application_mode()
    if app_mode == ApplicationMode.DEVELOPMENT:
        LOG.i("Running in a development environment")

    try:
        cm = ConfigurationManager()
        cm.load_configs(args)
        config = cm.get_server_config()
        setup_application(args, config)
        command = create_command(args)
        if args.command != AppCommand.SETUP:
            require_server_setup()

        return ExitStatus(command.execute())
    except Exception as ex:  # pylint: disable=broad-exception-caught
        LOG.e("Failed to run Fathom server")
        LOG.e(str(ex))
        LOG.d(str(ex), exc_info=True)
        return ExitStatus.FAILURE
