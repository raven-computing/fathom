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

from raven.fathom.base import User, UserState
from raven.fathom.base import Project
from raven.fathom.base import TableFormatter
from raven.fathom.base import log_stdout
from raven.fathom.client.config import ConfigurationManager
from raven.fathom.client.connection import Server, Result
from raven.fathom.client.connection import ServerConnectionException
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
            LOG.d(ex)
            return ExitStatus.SERVER_UNREACHABLE

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
            return self._create_user(server)
        if self.args.manage_command == AppCommand.LIST:
            return self._list_users(server)
        if self.args.manage_command == AppCommand.DELETE:
            return self._delete_user(server)
        if self.args.manage_command == AppCommand.ASSIGN:
            return self._assign_user(server)
        if self.args.manage_command == AppCommand.UNASSIGN:
            return self._unassign_user(server)

        raise ValueError(
            f"Invalid manage command '{self.args.manage_command}'"
        )

    def _manage_project(self, server: Server) -> ExitStatus:
        if self.args.manage_command == AppCommand.CREATE:
            return self._create_project(server)
        if self.args.manage_command == AppCommand.LIST:
            return self._list_projects(server)
        if self.args.manage_command == AppCommand.LIST_USERS:
            return self._list_project_users(server)
        if self.args.manage_command == AppCommand.DELETE:
            return self._delete_project(server)

        raise ValueError(
            f"Invalid manage command '{self.args.manage_command}'"
        )

    def _handle_messages_of(self, response: Result):
        if response.messages:
            LOG.v("Server responded with the following informational message:")
            for message in response.messages:
                LOG.v("%s", message)

        if response.warnings:
            LOG.w("Server responded with the following warnings:")
            for warning in response.warnings:
                LOG.w("%s", warning)

    def _handle_error_of(self, response: Result):
        for error in response.errors:
            LOG.e("%s", error)

    def _print_data(self, formatter: TableFormatter):
        log_stdout("")
        log_stdout(formatter.get_formatted_text())
        log_stdout("")

    def _create_user(self, server: Server):
        user = User(
            identifier=self.args.user_identifier,
            name=(
                self.args.user_name
                or self.args.user_identifier
            ),
        )
        response = server.create_user(user)
        if not response.ok:
            self._handle_error_of(response)
            return ExitStatus.FAILURE

        self._handle_messages_of(response)

        created_user = response.data
        LOG.i("Created client user %s", created_user.identifier)
        if created_user.state == UserState.ONBOARDING:
            LOG.i("The user can now sign up to activate his account")

        return ExitStatus.SUCCESS

    def _list_users(self, server: Server):
        response = server.list_users()
        if not response.ok:
            self._handle_error_of(response)
            return ExitStatus.FAILURE

        self._handle_messages_of(response)
        formatter = TableFormatter()
        formatter.set_headers("Identifier", "Name", "Role", "State")
        for user in response.data:
            role = "admin" if user.is_admin else "user"
            formatter.add_row(
                user.identifier, user.name, role, user.state
            )

        LOG.i("User list of %s", server.name or "Server")
        self._print_data(formatter)
        return ExitStatus.SUCCESS

    def _delete_user(self, server: Server):
        response = server.delete_user(self.args.user_identifier)
        if not response.ok:
            self._handle_error_of(response)
            return ExitStatus.FAILURE

        self._handle_messages_of(response)
        LOG.i(
            "Deleted user %s from %s",
            self.args.user_identifier,
            server.name or "Server",
        )
        return ExitStatus.SUCCESS

    def _assign_user(self, server: Server):
        response = server.assign_user_to_project(
            self.args.user_identifier,
            self.args.project_identifier,
        )
        if not response.ok:
            self._handle_error_of(response)
            return ExitStatus.FAILURE

        self._handle_messages_of(response)
        LOG.i(
            "Assigned user %s to project %s at %s",
            self.args.user_identifier,
            self.args.project_identifier,
            server.name or "Server",
        )
        return ExitStatus.SUCCESS

    def _unassign_user(self, server: Server):
        response = server.unassign_user_from_project(
            self.args.user_identifier,
            self.args.project_identifier,
        )
        if not response.ok:
            self._handle_error_of(response)
            return ExitStatus.FAILURE

        self._handle_messages_of(response)
        LOG.i(
            "Unassigned user %s from project %s at %s",
            self.args.user_identifier,
            self.args.project_identifier,
            server.name or "Server",
        )
        return ExitStatus.SUCCESS

    def _create_project(self, server: Server):
        project = Project(
            identifier=self.args.project_identifier,
            name=(
                self.args.project_name
                or self.args.project_identifier
            ),
            description=self.args.project_description,
        )
        response = server.create_project(project)
        if not response.ok:
            self._handle_error_of(response)
            return ExitStatus.FAILURE

        self._handle_messages_of(response)
        created_project = response.data
        LOG.i(
            "Created project %s at %s",
            created_project.identifier,
            server.name or "Server",
        )
        return ExitStatus.SUCCESS

    def _list_projects(self, server: Server):
        response = server.list_projects()
        if not response.ok:
            self._handle_error_of(response)
            return ExitStatus.FAILURE

        self._handle_messages_of(response)
        formatter = TableFormatter()
        formatter.set_headers("Identifier", "Name", "Description")
        for project in response.data:
            formatter.add_row(
                project.identifier,
                project.name,
                project.description,
            )

        LOG.i("Project list of %s", server.name or "Server")
        self._print_data(formatter)
        return ExitStatus.SUCCESS

    def _list_project_users(self, server: Server):
        response = server.list_project_users(
            self.args.project_identifier
        )
        if not response.ok:
            self._handle_error_of(response)
            return ExitStatus.FAILURE

        self._handle_messages_of(response)
        formatter = TableFormatter()
        formatter.set_headers("Identifier", "Name")
        for user in response.data:
            formatter.add_row(user.identifier, user.name)

        LOG.i(
            "All users assigned to project %s at %s",
            self.args.project_identifier,
            server.name or "Server",
        )
        self._print_data(formatter)
        return ExitStatus.SUCCESS

    def _delete_project(self, server: Server):
        response = server.delete_project(self.args.project_identifier)
        if not response.ok:
            self._handle_error_of(response)
            return ExitStatus.FAILURE

        self._handle_messages_of(response)
        LOG.i(
            "Deleted project %s from %s",
            self.args.project_identifier,
            server.name or "Server",
        )
        return ExitStatus.SUCCESS
