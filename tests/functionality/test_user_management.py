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

from unittest.mock import patch

from raven.fathom.base import File
from raven.fathom.client.cli import ExitStatus as ClientExitStatus
from raven.fathom.client.config import UserConfiguration
from raven.fathom.server.cli import ExitStatus as ServerExitStatus

from tests.functionality import TestCase
from tests.fixtures import ConfigurationFixture


class TestClientUserManagement(TestCase, ConfigurationFixture):
    """End-to-end tests for remote user management through the client CLI."""

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
            "alpha\tAlphanet Administrator\tadmin\tinitialized"
        )
        self.assertClientStdoutContains(
            "managed-user\tManaged User\tregular\tonboarding"
        )

        with patch(
            "raven.fathom.base._input.getpass.getpass",
            side_effect=["whatever", "secret-password", "secret-password"],
        ):
            self.client.execute("setup", "user", "managed-user")

        self.assertClientSuccess()
        self.assertClientStdoutContains("Initialized user 'managed-user'")
        stored_user = self.server.datastore.users().find_by_identifier(
            "managed-user"
        )
        assert stored_user is not None
        self.assertEqual(stored_user.state, "initialized")

        self.client.execute("manage", "user", "delete", "managed-user")

        self.assertClientSuccess()
        self.assertClientStdoutContains("Deleted user 'managed-user'")
        self.assertIsNone(
            self.server.datastore.users().find_by_identifier("managed-user")
        )

    def test_non_admin_client_is_rejected(self):
        config = self.configuration_user
        config[UserConfiguration.USER.USERNAME] = "test-user-1"
        config[UserConfiguration.USER.PASSWORD] = "123456"
        self.save_configuration(config, self.user_config_file)

        self.client.execute("manage", "user", "list")

        self.assertClientExitStatus(ClientExitStatus.FAILURE)
        self.assertClientStdoutContains(
            "Administrative privileges are required."
        )


class TestServerUserManagementCLI(TestCase):
    """Functionality tests for local user management via fathom-server."""

    _AUTO_START_SERVER = False

    def test_server_cli_can_create_list_and_delete_admin_user(self):
        self.server.execute(
            "user", "create", "local-admin",
            "--name", "Local Admin", "--admin"
        )

        self.assertEqual(
            ServerExitStatus.SUCCESS,
            self.server.command_exit_status
        )
        self.assertIn(
            "Created user 'local-admin' (admin, onboarding).",
            self.server.stdout
        )
        stored_user = self.server.datastore.users().find_by_identifier(
            "local-admin"
        )
        self.assertIsNotNone(stored_user)
        assert stored_user is not None
        permission = self.server.datastore.users().find_permission(stored_user)
        self.assertTrue(permission.is_admin)

        self.server.execute("user", "list")

        self.assertEqual(
            ServerExitStatus.SUCCESS,
            self.server.command_exit_status
        )
        self.assertIn(
            "User: 'local-admin'\tName: 'Local Admin'"
            "\tRole: 'admin'\tState: 'onboarding'",
            self.server.stdout
        )

        self.server.execute("user", "delete", "local-admin")

        self.assertEqual(
            ServerExitStatus.SUCCESS,
            self.server.command_exit_status
        )
        self.assertIn("Deleted user 'local-admin'.", self.server.stdout)
        self.assertIsNone(
            self.server.datastore.users().find_by_identifier("local-admin")
        )


if __name__ == "__main__":
    TestCase.run_tests()
