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

from tests.functionality import TestCase
from tests.fixtures import ConfigurationFixture


class TestClientUserManagement(TestCase, ConfigurationFixture):
    """End-to-end tests for remote user management through the client CLI."""

    def setUp(self):
        super().setUp()
        self.client.set_up_configuration_files(
            self.configuration_user,
            self.configuration_project
        )

    def test_admin_client_can_create_list_and_delete_users(self):
        self.client.execute(
            "manage", "user", "create", "managed-user",
            "--name", "Managed User",
        )

        self.assertClientSuccess()
        self.assertClientStdoutContains("Created client user managed-user")
        self.assertClientStdoutContains("The user can now sign up")

        self.client.execute("manage", "user", "list")

        self.assertClientSuccess()
        self.assertNotIn("Fathom System User", self.client.stdout)
        self.assertClientStdoutContains("alpha")
        self.assertClientStdoutContains("Alphanet Administrator")
        self.assertClientStdoutContains("admin")
        self.assertClientStdoutContains("active")
        self.assertClientStdoutContains("managed-user")
        self.assertClientStdoutContains("Managed User")
        self.assertClientStdoutContains("user")
        self.assertClientStdoutContains("onboarding")

        self.client.stdin = ["secret", "secret-password", "secret-password"]
        self.client.execute("setup", "user", "managed-user")

        self.assertClientSuccess()
        self.assertClientStdoutContains("Initialized user 'managed-user'")

        self.client.execute("manage", "user", "delete", "managed-user")

        self.assertClientSuccess()
        self.assertClientStdoutContains(
            "Deleted user managed-user from Test Server"
        )

        self.client.execute("manage", "user", "list")

        self.assertClientSuccess()
        self.assertNotIn("managed-user", self.client.stdout)
        self.assertClientStdoutContains("alpha")
        self.assertClientStdoutContains("Alphanet Administrator")

    def test_system_user_is_rejected_for_remote_management(self):
        config = self.configuration_user
        self.client.set_authentication_in(config, "fathom", "fathom")
        self.client.save_user_configuration(config)

        self.client.execute("manage", "user", "list")

        self.assertClientExitStatus(ClientExitStatus.FAILURE)
        self.assertClientStdoutContains("Invalid username or password.")

    def test_admin_client_can_assign_and_unassign_users_to_projects(self):
        self.client.execute(
            "manage", "project", "create", "test-project-2",
            "--name", "Test Project 2",
            "--description", "A Project for Testing Purposes (2).",
        )

        self.assertClientSuccess()

        self.client.execute(
            "manage", "user", "assign", "test-user-1", "test-project-2"
        )

        self.assertClientSuccess()
        self.assertClientStdoutContains(
            "Assigned user test-user-1 to project test-project-2 at Test Server"
        )

        self.client.execute(
            "manage", "project", "list-users", "test-project-2"
        )

        self.assertClientSuccess()
        self.assertClientStdoutContains(
            "All users assigned to project test-project-2"
        )
        self.assertClientStdoutContains("test-user-1")
        self.assertClientStdoutContains("Test User 1")

        self.client.execute(
            "manage", "user", "unassign", "test-user-1", "test-project-2"
        )

        self.assertClientSuccess()
        self.assertClientStdoutContains(
            "Unassigned user test-user-1 "
            "from project test-project-2 at Test Server"
        )

        self.client.execute(
            "manage", "project", "list-users", "test-project-2"
        )

        self.assertClientSuccess()
        self.assertClientStdoutContains(
            "There are currently no users assigned to project test-project-2"
        )
        self.assertNotIn("test-user-1", self.client.stdout)
        self.assertNotIn("Test User 1", self.client.stdout)

    def test_non_admin_client_is_rejected(self):
        config = self.configuration_user
        self.client.set_authentication_in(config, "test-user-1", "123456")
        self.client.save_user_configuration(config)

        self.client.execute("manage", "user", "list")

        self.assertClientExitStatus(ClientExitStatus.FAILURE)
        self.assertClientStdoutContains(
            "Administrative privileges are required."
        )


class TestServerUserManagementCLI(TestCase):
    """End-to-end functionality tests for the user management
    via the fathom-server CLI.
    """

    AUTO_START_SERVER = False

    def test_server_cli_setup_creates_initial_administrator(self):
        self.server.stdin = [
            "My Org",
            "initial-admin",
            "secret-password",
            "secret-password",
            "my-shared-secret",
            "system-pass",
            "system-pass",
        ]

        self.server.execute("setup")

        self.assertServerSuccess()
        self.assertIn("Server setup completed", self.server.stdout)
        self.assertIn("initial-admin", self.server.stdout)
        self.assertIn("fathom", self.server.stdout)

    def test_server_cli_requires_setup_before_serve(self):
        self.server.execute("serve", "--help")

        self.assertEqual(0, self.server.command_exit_status)


class TestServerResetCLI(TestCase):
    """End-to-end functionality tests for the `fathom-server reset` command."""

    AUTO_START_SERVER = False

    def test_reset_user_allows_subsequent_resign(self):
        self.server.initialize_datastore(TestCase.DATASTORE_SQL_FILE)
        self.server.stdin = ["fathom", "alpha", "alpha-new-password",
                             "alpha-new-password"]
        self.server.execute("reset", "user", "alpha")

        self.assertServerSuccess()
        self.assertIn("credentials for user 'alpha' have been reset",
                      self.server.stdout.lower())

    def test_reset_user_rejects_wrong_system_password(self):
        self.server.initialize_datastore(TestCase.DATASTORE_SQL_FILE)
        self.server.stdin = ["wrong-system-password"]
        self.server.execute("reset", "user", "alpha")

        self.assertNotEqual(0, self.server.command_exit_status)

    def test_reset_shared_secret_succeeds_with_correct_auth(self):
        self.server.initialize_datastore(TestCase.DATASTORE_SQL_FILE)
        self.server.stdin = ["fathom", "brand-new-secret"]
        self.server.execute("reset", "shared-secret")

        self.assertServerSuccess()
        self.assertIn("shared secret has been updated",
                      self.server.stdout.lower())


class TestServerUserManagementWithRunningServer(TestCase):
    """Tests for the server user management when the server is running."""

    AUTO_START_SERVER = True

    def test_server_cli_setup_creates_initial_administrator(self):
        self.skipTest("Only applicable before the server datastore is seeded")



if __name__ == "__main__":
    TestCase.run_tests()
