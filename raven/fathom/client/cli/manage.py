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
from raven.fathom.base import Project
from raven.fathom.client.config import ConfigurationManager
from raven.fathom.client.connection import Server
from raven.fathom.client.connection import (
    ServerConnectionException, ServerOperationException,
)
from raven.fathom.client.logging import Logger
from raven.fathom.client.locator import load_management_server_locator
from raven.fathom.client.authentication import load_client_authentication
from raven.fathom.client.cli.arguments import AppCommand
from raven.fathom.client.cli.command import ClientCommand
from raven.fathom.client.cli.status import ExitStatus


LOG = Logger.get()


class ManageCommand(ClientCommand):
    """Implementation of the `manage` CLI command."""

    def execute(self) -> int:
        try:
            return self._manage()
        except ServerConnectionException as ex:
            LOG.e(str(ex))
            return ExitStatus.SERVER_UNREACHABLE
        except ServerOperationException as ex:
            LOG.e(str(ex))
            return ExitStatus.FAILURE

    # Needs refactoring anyway!
    # pylint: disable=too-many-branches
    def _manage(self):
        config = ConfigurationManager()
        user_config = config.get_user_config()
        project_config = config.get_project_config()
        server = Server(
            load_management_server_locator(self.args, user_config),
            load_client_authentication(
                self.args,
                user_config,
                project_config
            ),
        )

        if self.args.manage_subject == AppCommand.USER:
            if self.args.manage_command == AppCommand.CREATE:
                user = User(
                    identifier=self.args.user_identifier,
                    name=(
                        self.args.user_name
                        or self.args.user_identifier
                    ),
                )
                created = server.create_user(user)
                LOG.i("Created user '%s'", created.identifier)
                return ExitStatus.SUCCESS

            if self.args.manage_command == AppCommand.LIST:
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

            if self.args.manage_command == AppCommand.DELETE:
                server.delete_user(self.args.user_identifier)
                LOG.i("Deleted user '%s'", self.args.user_identifier)
                return ExitStatus.SUCCESS

            if self.args.manage_command == AppCommand.ASSIGN:
                server.assign_user_to_project(
                    self.args.user_identifier,
                    self.args.project_identifier,
                )
                LOG.i(
                    "Assigned user '%s' to project '%s'",
                    self.args.user_identifier,
                    self.args.project_identifier,
                )
                return ExitStatus.SUCCESS

            if self.args.manage_command == AppCommand.UNASSIGN:
                server.unassign_user_from_project(
                    self.args.user_identifier,
                    self.args.project_identifier,
                )
                LOG.i(
                    "Unassigned user '%s' from project '%s'",
                    self.args.user_identifier,
                    self.args.project_identifier,
                )
                return ExitStatus.SUCCESS

            raise ValueError(
                f"Invalid manage command '{self.args.manage_command}'"
            )

        if self.args.manage_subject == AppCommand.PROJECT:
            if self.args.manage_command == AppCommand.CREATE:
                project = Project(
                    identifier=self.args.project_identifier,
                    name=(
                        self.args.project_name
                        or self.args.project_identifier
                    ),
                    description=self.args.project_description,
                )
                created = server.create_project(project)
                LOG.i("Created project '%s'", created.identifier)
                return ExitStatus.SUCCESS

            if self.args.manage_command == AppCommand.LIST:
                LOG.i("Fathom projects:")
                for project in server.list_projects():
                    LOG.i(
                        " | %s\t%s\t%s",
                        project.identifier,
                        project.name,
                        project.description,
                    )
                return ExitStatus.SUCCESS

            if self.args.manage_command == AppCommand.LIST_USERS:
                LOG.i(
                    "Users assigned to project '%s':",
                    self.args.project_identifier,
                )
                for user in server.list_project_users(
                    self.args.project_identifier
                ):
                    LOG.i(
                        " | %s\t%s",
                        user.identifier,
                        user.name,
                    )
                return ExitStatus.SUCCESS

            if self.args.manage_command == AppCommand.DELETE:
                server.delete_project(self.args.project_identifier)
                LOG.i(
                    "Deleted project '%s'",
                    self.args.project_identifier,
                )
                return ExitStatus.SUCCESS

        raise ValueError(
            f"Invalid manage subject '{self.args.manage_subject}'"
        )
