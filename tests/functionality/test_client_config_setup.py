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
"""Functionality tests for client configuration setup commands."""

from raven.fathom.base import ConfigurationLoader
from raven.fathom.client.config import UserConfiguration
from raven.fathom.client.config import ProjectConfiguration

from tests.functionality import TestCase


class TestClientUserConfigSetup(TestCase):
    """Functionality tests for client user config setup command."""

    AUTO_START_SERVER = False

    def test_setup_config_user_creates_default_file(self):
        config_file = self.client.get_user_configuration_file()
        self.assertFalse(config_file.exists())

        self.client.execute("setup", "config", "user")

        self.assertClientSuccess()
        self.assertTrue(config_file.is_regular_file())
        created_config = ConfigurationLoader(UserConfiguration).load(
            config_file
        )
        expected_default_config = UserConfiguration.default_configuration()
        self.assertEqual(expected_default_config, created_config)
        self.assertClientStdoutContains("Created user configuration file")

    def test_setup_config_user_keeps_existing_file(self):
        config_file = self.client.get_user_configuration_file()
        existing_config = UserConfiguration.default_configuration()
        existing_config[UserConfiguration.USER.USERNAME] = "sentinel-user"
        self.client.save_user_configuration(existing_config)

        self.client.execute("setup", "config", "user")

        self.assertClientSuccess()
        config = ConfigurationLoader(UserConfiguration).load(config_file)
        self.assertEqual(
            "sentinel-user",
            config[UserConfiguration.USER.USERNAME],
        )
        self.assertClientStdoutContains(
            "User configuration file already exists"
        )

    def test_setup_config_user_detects_alternate_config_filename(self):
        default_config_file = self.client.get_user_configuration_file()
        alternate_file = (
            default_config_file.get_parent_directory() / "User.config"
        )
        existing_config = UserConfiguration.default_configuration()
        existing_config[UserConfiguration.USER.USERNAME] = "alternate-user"
        alternate_file.get_parent_directory().create_directory_tree()
        ConfigurationLoader(UserConfiguration).store(
            existing_config,
            alternate_file,
        )

        self.client.execute("setup", "config", "user")

        self.assertClientSuccess()
        self.assertFalse(default_config_file.exists())
        self.assertTrue(alternate_file.is_regular_file())
        config = ConfigurationLoader(UserConfiguration).load(alternate_file)
        self.assertEqual(
            "alternate-user",
            config[UserConfiguration.USER.USERNAME],
        )
        self.assertClientStdoutContains(
            "User configuration file already exists"
        )


class TestClientProjectConfigSetup(TestCase):
    """Functionality tests for client project config setup command."""

    AUTO_START_SERVER = False

    def test_setup_config_project_creates_default_file(self):
        config_file = self.client.get_project_configuration_file()
        self.assertFalse(config_file.exists())

        self.client.execute("setup", "config", "project")

        self.assertClientSuccess()
        self.assertTrue(config_file.is_regular_file())
        created_config = ConfigurationLoader(ProjectConfiguration).load(
            config_file
        )
        expected_default_config = ProjectConfiguration.default_configuration()
        self.assertEqual(expected_default_config, created_config)
        self.assertClientStdoutContains("Created project configuration file")

    def test_setup_config_project_keeps_existing_file(self):
        config_file = self.client.get_project_configuration_file()
        existing_config = ProjectConfiguration.default_configuration()
        existing_config[ProjectConfiguration.PROJECT.NAME] = "Sentinel Name"
        self.client.save_project_configuration(existing_config)

        self.client.execute("setup", "config", "project")

        self.assertClientSuccess()
        config = ConfigurationLoader(ProjectConfiguration).load(config_file)
        self.assertEqual(
            "Sentinel Name",
            config[ProjectConfiguration.PROJECT.NAME],
        )
        self.assertClientStdoutContains(
            "Project configuration file already exists"
        )

    def test_setup_config_project_detects_alternate_config_filename(self):
        default_config_file = self.client.get_project_configuration_file()
        alternate_file = (
            default_config_file.get_parent_directory() / "docs/.fathom.config"
        )
        existing_config = ProjectConfiguration.default_configuration()
        existing_config[ProjectConfiguration.PROJECT.NAME] = "Alt Project"
        alternate_file.get_parent_directory().create_directory_tree()
        ConfigurationLoader(ProjectConfiguration).store(
            existing_config,
            alternate_file,
        )

        self.client.execute("setup", "config", "project")

        self.assertClientSuccess()
        self.assertFalse(default_config_file.exists())
        self.assertTrue(alternate_file.is_regular_file())
        config = ConfigurationLoader(ProjectConfiguration).load(alternate_file)
        self.assertEqual(
            "Alt Project",
            config[ProjectConfiguration.PROJECT.NAME],
        )
        self.assertClientStdoutContains(
            "Project configuration file already exists"
        )


if __name__ == "__main__":
    TestCase.run_tests()
