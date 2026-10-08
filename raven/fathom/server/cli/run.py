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
"""CLI command handling for the server serve command."""

from raven.fathom.base import ApplicationContext, ApplicationMode
from raven.fathom.server.cli.command import ServerCommand
from raven.fathom.server.core.logging import Logger
from raven.fathom.server.core.config import ConfigurationManager
from raven.fathom.server.core.config import ServerConfiguration
from raven.fathom.server.net.defaults import SERVER_ROOT_PATH_V1
from raven.fathom.server.net.http import assign
from raven.fathom.server.net.http import ServerHTTP
from raven.fathom.server.net.http import ServerApplication
from raven.fathom.server.net.http import HTTPServerStartException
from raven.fathom.server.controllers import InteractionController
from raven.fathom.server.controllers import PublicController
from raven.fathom.server.controllers import SignupController


LOG = Logger.get()


def _start_server(server: ServerHTTP):
    try:
        server.start()
    except HTTPServerStartException:
        LOG.e("Failed to start Fathom server")
        raise


class FathomServer(ServerApplication):
    """The Fathom server application."""

    def __init__(self):
        super().__init__()
        self.public = PublicController()
        self.user = SignupController()
        self.interact = InteractionController()

    def root_path(self):
        return SERVER_ROOT_PATH_V1


class RunServerCommand(ServerCommand):
    """Implementation of the default command to server client requests.

    Starts and runs the HTTP server application.
    """

    def execute(self) -> int:
        config = ConfigurationManager().get_server_config()
        port = config[ServerConfiguration.SERVER.PORT_LISTEN]
        LOG.i("Starting Fathom server on port %d", port)
        server = assign(
            ServerHTTP(FathomServer(), config, self.args.ready_event)
        )
        _start_server(server)
        app_mode = ApplicationContext.instance().get_application_mode()
        debug_mode_on = config[ServerConfiguration.SERVER.DEBUG_MODE_ENABLED]
        if app_mode == ApplicationMode.PRODUCTION and debug_mode_on:
            LOG.w(
                "The debug mode of the server is enabled. "
                "This is not suitable for a production environment."
            )

        server.run()
        LOG.i("Fathom server has been stopped")
        return server.status_code()
