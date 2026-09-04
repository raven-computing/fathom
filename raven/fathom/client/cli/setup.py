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
"""CLI command handling for setup actions."""

from raven.fathom.base import InputPrompt, User
from raven.fathom.base import ClientAuthentication
from raven.fathom.client.config import ConfigurationManager
from raven.fathom.client.connection import Server
from raven.fathom.client.connection import (
    ServerConnectionException, ServerOperationException,
)
from raven.fathom.client.logging import Logger
from raven.fathom.client.locator import load_management_server_locator
from raven.fathom.client.cli.command import Command
from raven.fathom.client.cli.status import ExitStatus


LOG = Logger.get()


class SetupCommand(Command):
    """Implementation of the `setup` CLI command."""

    def execute(self):
        try:
            return self._setup()
        except ServerConnectionException as ex:
            LOG.e(str(ex))
            return ExitStatus.SERVER_UNREACHABLE
        except ServerOperationException as ex:
            LOG.e(str(ex))
            return ExitStatus.FAILURE

    def _setup(self):
        if self.args.setup_subject != "user":
            raise ValueError(
                f"Invalid setup subject '{self.args.setup_subject}'"
            )

        prompt = InputPrompt.instance()
        identifier = self.args.setup_user_identifier or prompt.read(
            "User identifier: "
        )
        if not identifier:
            LOG.e("User identifier is required.")
            return ExitStatus.FAILURE

        shared_secret = prompt.read("Shared secret: ", secret=True)
        if not shared_secret:
            LOG.e("Shared secret is required.")
            return ExitStatus.FAILURE

        password = prompt.read("New password: ", secret=True)
        if not password:
            LOG.e("Password must not be empty.")
            return ExitStatus.FAILURE

        confirmation = prompt.read("Confirm password: ", secret=True)
        if password != confirmation:
            LOG.e("Password confirmation does not match.")
            return ExitStatus.FAILURE

        config = ConfigurationManager()
        user_config = config.get_user_config()
        location = load_management_server_locator(self.args, user_config)
        server = Server(
            location,
            authentication=ClientAuthentication(
                username=identifier,
                password=shared_secret,
            ),
        )
        server.setup_user(User(identifier=identifier, password=password))
        LOG.i("Initialized user '%s'", identifier)
        return ExitStatus.SUCCESS
