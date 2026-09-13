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
"""Functionality tests for project management commands."""

from raven.fathom.base import File
from raven.fathom.client.cli import ExitStatus as ClientExitStatus
from raven.fathom.client.config import UserConfiguration
from raven.fathom.server.cli import ExitStatus as ServerExitStatus

from tests.functionality import TestCase
from tests.fixtures import ConfigurationFixture


class TestClientProjectManagement(TestCase, ConfigurationFixture):
    """End-to-end tests for remote project management through the client CLI."""

    _DATASTORE_SQL_FILE = "default_datastore.sql"

    def setUp(self):
        super().setUp()
        self.user_config_file = File(
            self.client.env.home / ".config/fathom/user.cfg"
        )
        self.save_configuration(
            self.configuration_user,
            self.user_config_file,
        )

    def test_admin_client_can_create_list_and_delete_projects(self):
        self.client.execute(
            "manage", "project", "create", "managed-project",
            "--name", "Managed Project",
            "--description", "Managed project description",
        )

        self.assertClientSuccess()
        self.assertClientStdoutContains("Created project 'managed-project'")
        stored_project = self.server.datastore.projects().find_by_identifier(
            "managed-project"
        )
        self.assertIsNotNone(stored_project)

        self.client.execute("manage", "project", "list")

        self.assertClientSuccess()
        self.assertClientStdoutContains(
            "test-project-1\tTest Project 1\t"
            "A Project for Testing Purposes (1)."
        )
        self.assertClientStdoutContains(
            "managed-project\tManaged Project\t"
            "Managed project description"
        )

        self.client.execute("manage", "project", "delete", "managed-project")

        self.assertClientSuccess()
        self.assertClientStdoutContains("Deleted project 'managed-project'")
        self.assertIsNone(
            self.server.datastore.projects().find_by_identifier(
                "managed-project"
            )
        )

    def test_non_admin_client_is_rejected(self):
        config = self.configuration_user
        config[UserConfiguration.USER.USERNAME] = "test-user-1"
        config[UserConfiguration.USER.PASSWORD] = "123456"
        self.save_configuration(config, self.user_config_file)

        self.client.execute("manage", "project", "list")

        self.assertClientExitStatus(ClientExitStatus.FAILURE)
        self.assertClientStdoutContains(
            "Administrative privileges are required."
        )


class TestServerProjectManagementCLI(TestCase):
    """Functionality tests for local project management via fathom-server."""

    _AUTO_START_SERVER = False
    _DATASTORE_SQL_FILE = "default_datastore.sql"

    def test_server_cli_can_create_list_and_delete_project(self):
        self.server.execute(
            "project", "create", "local-project",
            "--name", "Local Project",
            "--description", "Local project description",
        )

        self.assertEqual(
            ServerExitStatus.SUCCESS,
            self.server.command_exit_status
        )
        self.assertIn(
            "Created project 'local-project'.",
            self.server.stdout
        )
        stored_project = self.server.datastore.projects().find_by_identifier(
            "local-project"
        )
        self.assertIsNotNone(stored_project)

        self.server.execute("project", "list")

        self.assertEqual(
            ServerExitStatus.SUCCESS,
            self.server.command_exit_status
        )
        self.assertIn(
            "Project: 'local-project'\tName: 'Local Project'"
            "\tDescription: 'Local project description'",
            self.server.stdout
        )

        self.server.execute("project", "delete", "local-project")

        self.assertEqual(
            ServerExitStatus.SUCCESS,
            self.server.command_exit_status
        )
        self.assertIn("Deleted project 'local-project'.", self.server.stdout)
        self.assertIsNone(
            self.server.datastore.projects().find_by_identifier("local-project")
        )


if __name__ == "__main__":
    TestCase.run_tests()
