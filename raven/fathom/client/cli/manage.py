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
from raven.fathom.base import TableFormatter
from raven.fathom.base import log_stdout
from raven.fathom.client.config import ConfigurationManager
from raven.fathom.client.connection import Server
from raven.fathom.client.connection import (
    ServerConnectionException, ServerOperationException,
)
from raven.fathom.client.logging import Logger
from raven.fathom.client.locator import load_server_locator
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

    def _manage(self):
        config = ConfigurationManager()
        user_config = config.get_user_config()
        project_config = config.get_project_config()
        location = load_server_locator(self.args, user_config, project_config)
        server = Server(
            location,
            load_client_authentication(
                self.args,
                user_config,
                project_config,
                location.server_name,
            ),
        )

        if self.args.manage_subject == AppCommand.USER:
            return self._manage_user(server)
        if self.args.manage_subject == AppCommand.PROJECT:
            return self._manage_project(server)

        raise ValueError(
            f"Invalid manage subject '{self.args.manage_subject}'"
        )

    def _manage_user(self, server: Server) -> ExitStatus:
        if self.args.manage_command == AppCommand.CREATE:
            self._create_user(server)
        elif self.args.manage_command == AppCommand.LIST:
            self._list_users(server)
        elif self.args.manage_command == AppCommand.DELETE:
            self._delete_user(server)
        elif self.args.manage_command == AppCommand.ASSIGN:
            self._assign_user(server)
        elif self.args.manage_command == AppCommand.UNASSIGN:
            self._unassign_user(server)
        else:
            raise ValueError(
                f"Invalid manage command '{self.args.manage_command}'"
            )

        return ExitStatus.SUCCESS

    def _manage_project(self, server: Server) -> ExitStatus:
        if self.args.manage_command == AppCommand.CREATE:
            self._create_project(server)
        elif self.args.manage_command == AppCommand.LIST:
            self._list_projects(server)
        elif self.args.manage_command == AppCommand.LIST_USERS:
            self._list_project_users(server)
        elif self.args.manage_command == AppCommand.DELETE:
            self._delete_project(server)
        else:
            raise ValueError(
                f"Invalid manage command '{self.args.manage_command}'"
            )

        return ExitStatus.SUCCESS

    def _create_user(self, server: Server):
        user = User(
            identifier=self.args.user_identifier,
            name=(
                self.args.user_name
                or self.args.user_identifier
            ),
        )
        created = server.create_user(user)
        LOG.i("Created user '%s'", created.identifier)

    def _list_users(self, server: Server):
        users = server.list_users()
        formatter = TableFormatter(
            title="Fathom users:"
        ).set_headers("Identifier", "Name", "Role", "State")
        for user in users:
            role = "admin" if user.is_admin else "regular"
            formatter.add_row(
                user.identifier, user.name, role, user.state
            )

        log_stdout(formatter.get_formatted_text())

    def _delete_user(self, server: Server):
        server.delete_user(self.args.user_identifier)
        LOG.i("Deleted user '%s'", self.args.user_identifier)

    def _assign_user(self, server: Server):
        server.assign_user_to_project(
            self.args.user_identifier,
            self.args.project_identifier,
        )
        LOG.i(
            "Assigned user '%s' to project '%s'",
            self.args.user_identifier,
            self.args.project_identifier,
        )

    def _unassign_user(self, server: Server):
        server.unassign_user_from_project(
            self.args.user_identifier,
            self.args.project_identifier,
        )
        LOG.i(
            "Unassigned user '%s' from project '%s'",
            self.args.user_identifier,
            self.args.project_identifier,
        )

    def _create_project(self, server: Server):
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

    def _list_projects(self, server: Server):
        projects = server.list_projects()
        formatter = TableFormatter(
            title="Fathom projects:"
        ).set_headers("Identifier", "Name", "Description")
        for project in projects:
            formatter.add_row(
                project.identifier,
                project.name,
                project.description,
            )

        log_stdout(formatter.get_formatted_text())

    def _list_project_users(self, server: Server):
        users = server.list_project_users(
            self.args.project_identifier
        )
        formatter = TableFormatter(
            title="Users assigned to "
                    f"project '{self.args.project_identifier}':"
        ).set_headers("Identifier", "Name")
        for user in users:
            formatter.add_row(user.identifier, user.name)

        log_stdout(formatter.get_formatted_text())

    def _delete_project(self, server: Server):
        server.delete_project(self.args.project_identifier)
        LOG.i(
            "Deleted project '%s'",
            self.args.project_identifier,
        )
