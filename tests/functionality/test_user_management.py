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
"""Functionality tests for user management commands."""

from raven.fathom.client.cli import ExitStatus as ClientExitStatus
from raven.fathom.client.config import UserConfiguration

from tests.functionality import TestCase
from tests.fixtures import ConfigurationFixture


class TestClientUserManagement(TestCase, ConfigurationFixture):
    """End-to-end tests for remote user management through the client CLI."""

    _DATASTORE_SQL_FILE = "default_datastore.sql"

    def setUp(self):
        super().setUp()
        self.set_up_client_configuration_files(self.client.env)

    def test_admin_client_can_create_list_and_delete_users(self):
        self.client.execute(
            "manage", "user", "create", "managed-user",
            "--name", "Managed User",
        )

        self.assertClientSuccess()
        self.assertClientStdoutContains("Created user 'managed-user'")

        self.client.execute("manage", "user", "list")

        self.assertClientSuccess()
        self.assertClientStdoutContains(
            "alpha\tAlphanet Administrator\tadmin\tactive"
        )
        self.assertClientStdoutContains(
            "managed-user\tManaged User\tregular\tonboarding"
        )

        self.client.stdin = ["whatever", "secret-password", "secret-password"]
        self.client.execute("setup", "user", "managed-user")

        self.assertClientSuccess()
        self.assertClientStdoutContains("Initialized user 'managed-user'")

        self.client.execute("manage", "user", "delete", "managed-user")

        self.assertClientSuccess()
        self.assertClientStdoutContains("Deleted user 'managed-user'")

        self.client.execute("manage", "user", "list")

        self.assertClientSuccess()
        self.assertNotIn(
            "managed-user\tManaged User\tregular\tonboarding",
            self.client.stdout
        )
        self.assertClientStdoutContains(
            "alpha\tAlphanet Administrator\tadmin\tactive"
        )

    def test_non_admin_client_is_rejected(self):
        config = self.configuration_user
        config[UserConfiguration.USER.USERNAME] = "test-user-1"
        config[UserConfiguration.USER.PASSWORD] = "123456"
        self.save_configuration(
            config,
            self.get_user_configuration_file(self.client.env)
        )

        self.client.execute("manage", "user", "list")

        self.assertClientExitStatus(ClientExitStatus.FAILURE)
        self.assertClientStdoutContains(
            "Administrative privileges are required."
        )


class TestServerUserManagementCLI(TestCase):
    """End-to-end functionality tests for the user management
    via the fathom-server CLI.
    """

    _AUTO_START_SERVER = False

    def test_server_cli_can_create_list_and_delete_admin_user(self):
        self.server.execute(
            "user", "create", "local-admin",
            "--name", "Local Admin", "--admin"
        )

        self.assertServerSuccess()
        self.assertIn(
            "Created user 'local-admin' (admin, onboarding).",
            self.server.stdout
        )

        self.server.execute("user", "list")

        self.assertServerSuccess()
        self.assertIn(
            "User: 'local-admin'\tName: 'Local Admin'"
            "\tRole: 'admin'\tState: 'onboarding'",
            self.server.stdout
        )

        self.server.execute("user", "delete", "local-admin")

        self.assertServerSuccess()
        self.assertIn("Deleted user 'local-admin'.", self.server.stdout)

        self.server.execute("user", "list")

        self.assertServerSuccess()
        self.assertNotIn("local-admin", self.server.stdout)
        self.assertNotIn("Local Admin", self.server.stdout)


class TestServerUserManagementWithRunningServer(TestServerUserManagementCLI):
    """Same tests as `TestServerUserManagementCLI` but with the
    server already running.
    """

    _AUTO_START_SERVER = True


if __name__ == "__main__":
    TestCase.run_tests()
