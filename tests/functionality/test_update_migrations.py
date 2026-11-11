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

from raven.fathom.base import File, ApplicationContext, ApplicationMode
from raven.fathom.base import read_version_file, write_version_file
from raven.fathom.server.core.version import Version

from tests.functionality import TestCase
from tests.fixtures import ConfigurationFixture


class TestServerUpdateMigrations(TestCase, ConfigurationFixture):
    """End-to-end functionality test for updates.

    Tests that the server can migrate from a baseline version to
    the latest available version.
    """

    AUTO_START_SERVER = False

    def setUp(self):
        super().setUp()
        self.client.set_up_configuration_files(
            self.configuration_user,
            self.configuration_project
        )
        self.work_dir = File(self.server.env.cwd)
        with ApplicationContext.create_instance().initialize(
            ApplicationMode.TESTING, self.work_dir
        ):
            self.current_version = Version.current()
            self.assertIsNotNone(self.current_version)

    def assert_can_interact_with_server_via_cli(self):
        """Asserts that server CLI commands work."""
        self.server.stdin = ["fathom"]
        self.server.execute("user", "list")

        self.assertServerSuccess()
        self.assertIn("alpha", self.server.stdout)
        self.assertIn("test-user-1", self.server.stdout)

        self.server.stdin = ["fathom"]
        self.server.execute("project", "list")

        self.assertServerSuccess()
        self.assertIn("test-project-1", self.server.stdout)

    def assert_can_interact_with_server_via_client(self):
        """Asserts that the client can interact with the server."""
        self.client.execute("manage", "user", "list")

        self.assertClientSuccess()
        self.assertClientStdoutContains("alpha")
        self.assertClientStdoutContains("test-user-1")

    def test_server_can_migrate_from_baseline_version_to_latest_version(self):
        baseline_version = Version(0, 0, 1)
        write_version_file(self.work_dir, baseline_version)
        self.server.initialize_datastore(
            "baseline_datastore.sql",
            create_schema=False,
        )

        self.server.start()

        self.assertServerIsRunning()
        self.assert_can_interact_with_server_via_cli()

        self.server.shutdown()

        self.assertServerSuccess()
        updated_version = read_version_file(self.work_dir)
        self.assertIsNotNone(updated_version)
        self.assertEqual(self.current_version, updated_version)

        self.server.execute("--version")

        self.assertIn(str(self.current_version), self.server.stdout)

        self.server.start()

        self.assert_can_interact_with_server_via_client()

        self.server.shutdown()

        self.assertServerSuccess()


if __name__ == "__main__":
    TestCase.run_tests()
