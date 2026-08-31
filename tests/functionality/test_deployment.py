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
"""Functionality tests for the deployment feature."""

from raven.fathom.base import File
from raven.fathom.client.cli import ExitStatus
from raven.fathom.client.config import UserConfiguration, ProjectConfiguration

from tests.functionality import TestCase
from tests.fixtures import ProjectFixture, ConfigurationFixture


class TestDeployment(TestCase, ProjectFixture, ConfigurationFixture):
    """Functionality test case to test that the client can deploy resources.

    Tests here verify the end-to-end behaviour of the `deploy` CLI command,
    covering successful deployments as well as various failure conditions.
    """

    _DATASTORE_SQL_FILE = "default_datastore.sql"

    def setUp(self):
        super().setUp()
        self.client.env.cwd /= self.project.identifier
        self.project_build_dir = File(self.client.env.cwd / "build")
        self.set_up_project_files(
            self.project_build_dir
        )
        self.project_config_file = File(self.client.env.cwd / "fathom.cfg")
        self.save_configuration(
            self.configuration_project,
            self.project_config_file
        )
        self.user_config_file = File(
            self.client.env.home / ".config/fathom/user.cfg"
        )
        self.save_configuration(
            self.configuration_user,
            self.user_config_file
        )

    def test_client_can_deploy_resources(self):
        self.client.execute("deploy")

        self.assertClientSuccess()
        self.assertServerIsRunning()

    def test_client_with_invalid_username_is_rejected(self):
        config = self.configuration_user
        config[UserConfiguration.USER.USERNAME] = "unknown-user"
        self.save_configuration(config, self.user_config_file)

        self.client.execute("deploy")

        self.assertClientExitStatus(ExitStatus.FAILURE)

    def test_client_with_invalid_password_credentials_is_rejected(self):
        config = self.configuration_user
        config[UserConfiguration.USER.PASSWORD] = "invalid-password"
        self.save_configuration(config, self.user_config_file)

        self.client.execute("deploy")

        self.assertClientExitStatus(ExitStatus.FAILURE)

    def test_client_using_invalid_project_name_is_rejected(self):
        config = self.configuration_project
        config[ProjectConfiguration.PROJECT.IDENTIFIER] = "invalid-project-id"
        config[ProjectConfiguration.PROJECT.NAME] = "Unknown Project"
        config[ProjectConfiguration.PROJECT.DESCRIPTION] = "I don't know"
        self.save_configuration(config, self.project_config_file)

        self.client.execute("deploy")

        self.assertClientExitStatus(ExitStatus.FAILURE)

    def test_client_fails_gracefully_when_server_unavailable(self):
        self.server.shutdown()

        self.client.execute("deploy")

        self.assertClientExitStatus(ExitStatus.SERVER_UNREACHABLE)

    def test_client_with_missing_project_config_fails_gracefully(self):
        self.project_config_file.remove()

        self.client.execute("deploy")

        self.assertClientExitStatus(ExitStatus.FAILURE)

    def test_client_with_invalid_assets_path_is_rejected(self):
        config = self.configuration_project
        config[ProjectConfiguration.PROJECT.ASSETS] = "something_invalid"
        self.save_configuration(config, self.project_config_file)

        self.client.execute("deploy")

        self.assertClientExitStatus(ExitStatus.FAILURE)
        self.assertClientStdoutContains(
            "Failed to load documentation resources "
            "from project assets directory",
        )

    def test_client_can_deploy_using_cli_credential_arguments(self):
        config = self.configuration_user
        config[UserConfiguration.USER.USERNAME] = "wrong-user"
        config[UserConfiguration.USER.PASSWORD] = "wrong-password"
        self.save_configuration(config, self.user_config_file)

        self.client.execute("--user", "alpha", "--password", "alpha", "deploy")

        self.assertClientSuccess()


if __name__ == "__main__":
    TestCase.run_tests()
