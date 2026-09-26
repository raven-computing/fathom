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
from raven.fathom.base import Project
from raven.fathom.client.cli import ExitStatus
from raven.fathom.client.config import UserConfiguration, ProjectConfiguration
from raven.fathom.server.config import ServerConfiguration

from tests.functionality import TestCase
from tests.fixtures import ProjectFixture, ConfigurationFixture


# pylint: disable=invalid-name


class TestDeployment(TestCase, ProjectFixture, ConfigurationFixture):
    """Functionality test case to test that the client can deploy resources.

    Tests here verify the end-to-end behaviour of the `deploy` CLI command,
    covering successful deployments as well as various failure conditions.
    """

    def setUp(self):
        super().setUp()
        self.client.env.cwd /= self.project.identifier
        self.project_build_dir = File(self.client.env.cwd / "build")
        self.set_up_project_files(
            self.project_build_dir
        )
        self.client.set_up_configuration_files(
            self.configuration_user,
            self.configuration_project
        )
        self.server.set_up_configuration_files()

    def assertProjectIsDeployedOnServer(self, deployed_project: Project):
        """Asserts that content from the specified project's build directory
        on the client side was fully deployed to the server's site
        target directory.
        """
        project_src_dir = self.get_project_resource_directory()
        config = self.server.get_configuration()
        assert deployed_project.version is not None
        deployed_project_dir = (
            self.get_server_directory()
            / config[ServerConfiguration.SERVER.DEPLOYMENT_SITE_DIRECTORY]
            / deployed_project.identifier
            / deployed_project.version.identifier
        )
        expected_files = set(
            str(file.path.relative_to(project_src_dir))
            for file in project_src_dir.list_all_files()
        )
        self.assertDirectoryExists(deployed_project_dir)
        self.assertDirectoryContent(
            deployed_project_dir,
            expected_files,
            include_subdirectories=True
        )

    def test_client_can_deploy_resources(self):
        self.client.execute("deploy")

        self.assertClientSuccess()
        self.assertClientStdoutContains("Deployment SUCCESSFUL")
        self.assertServerIsRunning()
        self.assertProjectIsDeployedOnServer(self.project)

    def test_client_with_invalid_username_is_rejected(self):
        config = self.configuration_user
        config[UserConfiguration.SERVER.USERNAME] = "unknown-user"
        self.client.save_user_configuration(config)

        self.client.execute("deploy")

        self.assertClientExitStatus(ExitStatus.FAILURE)

    def test_client_with_invalid_password_credentials_is_rejected(self):
        config = self.configuration_user
        config[UserConfiguration.SERVER.PASSWORD] = "invalid-password"
        self.client.save_user_configuration(config)

        self.client.execute("deploy")

        self.assertClientExitStatus(ExitStatus.FAILURE)

    def test_client_using_invalid_project_name_is_rejected(self):
        config = self.configuration_project
        config[ProjectConfiguration.PROJECT.IDENTIFIER] = "invalid-project-id"
        config[ProjectConfiguration.PROJECT.NAME] = "Unknown Project"
        config[ProjectConfiguration.PROJECT.DESCRIPTION] = "I don't know"
        self.client.save_project_configuration(config)

        self.client.execute("deploy")

        self.assertClientExitStatus(ExitStatus.FAILURE)

    def test_client_fails_gracefully_when_server_unavailable(self):
        self.server.shutdown()

        self.client.execute("deploy")

        self.assertClientExitStatus(ExitStatus.SERVER_UNREACHABLE)

    def test_client_with_missing_project_config_fails_gracefully(self):
        self.client.get_project_configuration_file().remove()

        self.client.execute("deploy")

        self.assertClientExitStatus(ExitStatus.FAILURE)

    def test_client_with_invalid_assets_path_is_rejected(self):
        config = self.configuration_project
        config[ProjectConfiguration.PROJECT.ASSETS] = "something_invalid"
        self.client.save_project_configuration(config)

        self.client.execute("deploy")

        self.assertClientExitStatus(ExitStatus.FAILURE)
        self.assertClientStdoutContains(
            "Failed to load documentation resources "
            "from project assets directory",
        )

    def test_client_can_deploy_using_cli_credential_arguments(self):
        config = self.configuration_user
        server_config = config.get_repeatable_sections(
            UserConfiguration.SERVER
        )[0]
        server_config[UserConfiguration.SERVER.USERNAME] = "wrong-user"
        server_config[UserConfiguration.SERVER.PASSWORD] = "wrong-password"
        self.client.save_user_configuration(config)

        self.client.execute("--user", "alpha", "--password", "alpha", "deploy")

        self.assertClientSuccess()
        self.assertProjectIsDeployedOnServer(self.project)


if __name__ == "__main__":
    TestCase.run_tests()
