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
"""Unit tests for the client authentication module."""

from raven.fathom.base import ClientAuthentication
from raven.fathom.base import Configuration, ConfigurationSection
from raven.fathom.base.testing import TestEnvironment, SystemInputPromptMock
from raven.fathom.client.authentication import (
    load_client_authentication,
    ENVIRONMENT_VARIABLE_USER_NAME,
    ENVIRONMENT_VARIABLE_USER_PASSWORD
)
from raven.fathom.client.config import UserConfiguration, ProjectConfiguration
from raven.fathom.client.cli.arguments import ArgumentsCLI

from tests.unit import TestCase


class TestClientAuthentication(TestCase):
    """Tests the `load_client_authentication()` function."""

    def setUp(self):
        super().setUp()
        # User data from CLI arguments
        self.user_name_cli = "TestUserCLI"
        self.user_password_cli = "TestPasswordCLI"
        self.cli_args = ArgumentsCLI(
            user=self.user_name_cli,
            password=self.user_password_cli
        )
        # User data from user configuration file
        self.server_name = "Primary"
        self.user_name_config = "TestUserConfig"
        self.user_password_config = "TestPasswordConfig"
        user_server = ConfigurationSection(
            UserConfiguration.SERVER,
            sequence_number=1
        )
        user_server.set_value(
            UserConfiguration.SERVER.NAME,
            self.server_name
        )
        user_server.set_value(
            UserConfiguration.SERVER.USERNAME,
            self.user_name_config
        )
        user_server.set_value(
            UserConfiguration.SERVER.PASSWORD,
            self.user_password_config
        )
        self.user_config = Configuration()
        self.user_config.add_section(user_server)
        # Server data from project configuration file
        self.project_config = Configuration()
        self.project_server = ConfigurationSection(ProjectConfiguration.SERVER)
        self.project_server.set_value(
            ProjectConfiguration.SERVER.NAME,
            self.server_name
        )
        self.project_config.add_section(self.project_server)
        # User data from environment variables
        self.user_name_env = "TestUserEnvVar"
        self.user_password_env = "TestPasswordEnvVar"
        test_env = TestEnvironment.instance()
        test_env.env_vars[ENVIRONMENT_VARIABLE_USER_NAME] = self.user_name_env
        test_env.env_vars[ENVIRONMENT_VARIABLE_USER_PASSWORD] = (
            self.user_password_env
        )
        # User data from user input
        self.user_name_in = "TestUserInput"
        self.user_password_in = "TestPasswordInput"
        test_input = SystemInputPromptMock.instance()
        test_input.inputs.append(self.user_name_in)
        test_input.inputs.append(self.user_password_in)

    def test_returns_auth_from_user_config_when_project_server_matches(self):
        TestEnvironment.instance().env_vars.clear()
        auth = load_client_authentication(
            ArgumentsCLI(),
            self.user_config,
            self.project_config
        )
        self.assertIsInstance(auth, ClientAuthentication)
        self.assertEqual(auth.username, self.user_name_config)
        self.assertEqual(auth.password, self.user_password_config)

    def test_returns_auth_from_project_config(self):
        TestEnvironment.instance().env_vars.clear()
        project_user_name_config = "TestProjectUsernameConfig"
        self.project_server.set_value(
            ProjectConfiguration.SERVER.USERNAME,
            project_user_name_config
        )

        auth = load_client_authentication(
            ArgumentsCLI(),
            self.user_config,
            self.project_config
        )

        self.assertIsInstance(auth, ClientAuthentication)
        self.assertEqual(auth.username, project_user_name_config)
        self.assertEqual(auth.password, self.user_password_config)

    def test_project_config_overrides_matching_user_server_values(self):
        TestEnvironment.instance().env_vars.clear()
        self.project_server.set_value(
            ProjectConfiguration.SERVER.USERNAME,
            "ProjectUser"
        )
        self.project_server.set_value(
            ProjectConfiguration.SERVER.PASSWORD,
            "ProjectPassword"
        )

        auth = load_client_authentication(
            ArgumentsCLI(),
            self.user_config,
            self.project_config
        )

        self.assertIsInstance(auth, ClientAuthentication)
        self.assertEqual(auth.username, "ProjectUser")
        self.assertEqual(auth.password, "ProjectPassword")

    def test_project_config_missing_password_falls_back_to_user_server(self):
        TestEnvironment.instance().env_vars.clear()
        self.project_server.set_value(
            ProjectConfiguration.SERVER.USERNAME,
            "ProjectUser"
        )

        auth = load_client_authentication(
            ArgumentsCLI(),
            self.user_config,
            self.project_config
        )

        self.assertIsInstance(auth, ClientAuthentication)
        self.assertEqual(auth.username, "ProjectUser")
        self.assertEqual(auth.password, self.user_password_config)

    def test_env_overrides_project_and_user_config(self):
        auth = load_client_authentication(
            ArgumentsCLI(),
            self.user_config,
            self.project_config
        )
        self.assertIsInstance(auth, ClientAuthentication)
        self.assertEqual(auth.username, self.user_name_env)
        self.assertEqual(auth.password, self.user_password_env)

    def test_cli_overrides_env_and_config(self):
        auth = load_client_authentication(
            self.cli_args,
            self.user_config,
            self.project_config
        )
        self.assertIsInstance(auth, ClientAuthentication)
        self.assertEqual(auth.username, self.user_name_cli)
        self.assertEqual(auth.password, self.user_password_cli)

    def test_returns_auth_with_all_sources_none_prompts_user(self):
        TestEnvironment.instance().env_vars.clear()
        auth = load_client_authentication(
            ArgumentsCLI(),
            Configuration(),
            Configuration()
        )
        self.assertIsInstance(auth, ClientAuthentication)
        self.assertEqual(auth.username, self.user_name_in)
        self.assertEqual(auth.password, self.user_password_in)

    def test_prompt_only_for_missing_user_name(self):
        env = TestEnvironment.instance()
        env.env_vars[ENVIRONMENT_VARIABLE_USER_NAME] = ""
        auth = load_client_authentication(
            ArgumentsCLI(),
            Configuration(),
            Configuration()
        )
        self.assertIsInstance(auth, ClientAuthentication)
        self.assertEqual(auth.username, self.user_name_in)
        self.assertEqual(auth.password, self.user_password_env)

    def test_prompt_only_for_missing_user_password(self):
        # Reverse to get the password first
        SystemInputPromptMock.instance().inputs.reverse()
        env = TestEnvironment.instance()
        env.env_vars[ENVIRONMENT_VARIABLE_USER_PASSWORD] = ""
        auth = load_client_authentication(
            ArgumentsCLI(),
            Configuration(),
            Configuration()
        )
        self.assertIsInstance(auth, ClientAuthentication)
        self.assertEqual(auth.username, self.user_name_env)
        self.assertEqual(auth.password, self.user_password_in)

    def test_no_auth_provided_returns_empty_auth(self):
        TestEnvironment.instance().env_vars.clear()
        SystemInputPromptMock.instance().inputs.clear()
        auth = load_client_authentication(
            ArgumentsCLI(),
            Configuration(),
            Configuration()
        )
        self.assertIsInstance(auth, ClientAuthentication)
        self.assertEqual(auth.username, "")
        self.assertEqual(auth.password, "")


if __name__ == "__main__":
    TestCase.run_tests()
