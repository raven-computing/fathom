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
"""CLI command handling for server-side management operations."""

from raven.fathom.base import User
from raven.fathom.client.config import ConfigurationManager
from raven.fathom.client.connection import Server
from raven.fathom.client.connection import (
    ServerConnectionException, ServerOperationException,
)
from raven.fathom.client.logging import Logger
from raven.fathom.client.locator import load_management_server_locator
from raven.fathom.client.authentication import load_client_authentication
from raven.fathom.client.cli.command import Command
from raven.fathom.client.cli.status import ExitStatus


LOG = Logger.get()


class ManageCommand(Command):
    """Implementation of the `manage` CLI command."""

    def execute(self):
        try:
            return self._manage()
        except ServerConnectionException as ex:
            LOG.e(str(ex))
            return ExitStatus.SERVER_UNREACHABLE
        except ServerOperationException as ex:
            LOG.e(str(ex))
            return ExitStatus.FAILURE

    def _manage(self):
        if self.args.manage_subject != "user":
            raise ValueError(
                f"Invalid manage subject '{self.args.manage_subject}'"
            )

        config = ConfigurationManager()
        user_config = config.get_user_config()
        server = Server(
            load_management_server_locator(self.args, user_config),
            load_client_authentication(self.args, user_config),
        )

        if self.args.manage_command == "create":
            user = User(
                identifier=self.args.managed_user_identifier,
                name=(
                    self.args.managed_user_name
                    or self.args.managed_user_identifier
                ),
            )
            created = server.create_user(user)
            LOG.i("Created user '%s'", created.identifier)
            return ExitStatus.SUCCESS

        if self.args.manage_command == "list":
            users = server.list_users()
            for user in users:
                role = "admin" if user.is_admin else "regular"
                LOG.i("Fathom users:")
                LOG.i(
                    " | %s\t%s\t%s\t%s",
                    user.identifier,
                    user.name,
                    role,
                    user.state
                )
            return ExitStatus.SUCCESS

        if self.args.manage_command == "delete":
            server.delete_user(self.args.managed_user_identifier)
            LOG.i("Deleted user '%s'", self.args.managed_user_identifier)
            return ExitStatus.SUCCESS

        raise ValueError(
            f"Invalid manage command '{self.args.manage_command}'"
        )
