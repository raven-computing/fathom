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
"""Test fixtures for application configurations."""

from raven.fathom.base import Configuration, ConfigurationSection
from raven.fathom.base import ConfigurationLoader
from raven.fathom.base import File
from raven.fathom.client.config import UserConfiguration, ProjectConfiguration
from raven.fathom.server.defaults import DEFAULT_SERVER_PORT

from tests.common import FathomTestFixture


class ConfigurationFixture(FathomTestFixture):
    """Test fixture to set up application configurations."""

    @property
    def configuration_user(self) -> Configuration:
        """A `Configuration` object test fixture for user configuration."""
        config = Configuration()
        user = ConfigurationSection(UserConfiguration.USER)
        user[UserConfiguration.USER.LOGGING_ENABLED] = True
        user[UserConfiguration.USER.USERNAME] = "alpha"
        user[UserConfiguration.USER.PASSWORD] = "alpha"
        config.add_section(user)
        server_1 = ConfigurationSection(
            UserConfiguration.SERVER,
            sequence_number=1
        )
        server_1[UserConfiguration.SERVER.NAME] = "Test Server"
        server_1[UserConfiguration.SERVER.DOMAIN] = "localhost"
        server_1[UserConfiguration.SERVER.USERNAME] = "alpha"
        server_1[UserConfiguration.SERVER.PASSWORD] = "alpha"
        server_1[UserConfiguration.SERVER.PORT] = DEFAULT_SERVER_PORT
        server_1[UserConfiguration.SERVER.TRANSPORT_SECURE] = False
        config.add_section(server_1)
        return config

    @property
    def configuration_project(self) -> Configuration:
        """A `Configuration` object test fixture for project configuration."""
        config = Configuration()
        project = ConfigurationSection(ProjectConfiguration.PROJECT)
        project[ProjectConfiguration.PROJECT.IDENTIFIER] = "test-project-1"
        project[ProjectConfiguration.PROJECT.NAME] = "Test-Project-1"
        project[ProjectConfiguration.PROJECT.DESCRIPTION] = (
            "A Project for Testing Purposes (1)."
        )
        project[ProjectConfiguration.PROJECT.VERSION] = "1.0.0"
        project[ProjectConfiguration.PROJECT.DOMAIN] = "localhost"
        project[ProjectConfiguration.PROJECT.ASSETS] = "build"
        config.add_section(project)
        server = ConfigurationSection(ProjectConfiguration.SERVER)
        server[ProjectConfiguration.SERVER.NAME] = "Test Server"
        config.add_section(server)
        return config

    def save_configuration(self, config: Configuration, target: File):
        """Sets up a configuration file with the given `Configuration` object
        at the given target `File` path.
        """
        target.get_parent_directory().create_directory_tree()
        ConfigurationLoader().store(config, target)
