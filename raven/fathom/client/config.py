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
"""Client configuration definitions.

The primary API is provided by the `ConfigurationManager` class. It can be
directly instantiated and provides methods to obtain `Configuration` objects
which store various global application configuration values.
"""

import itertools
import threading

from typing import TYPE_CHECKING, Final

from raven.fathom.base import Configuration, ConfigurationDefinition
from raven.fathom.base import ConfigurationKey, ConfigurationSectionKey
from raven.fathom.base import ConfigurationLoader
from raven.fathom.base import File, FileSize
from raven.fathom.base import SystemEnvironment
from raven.fathom.base.context import APPLICATION_PROJECT_ID
from raven.fathom.base.decorators import singleton
from raven.fathom.client.logging import Logger

if TYPE_CHECKING:
    from raven.fathom.client.cli import ArgumentsCLI


LOG = Logger.get()


class UserConfigurationSection(ConfigurationSectionKey):
    """Definition of configuration keys within the user config section."""

    LOGGING_ENABLED = ConfigurationKey[bool](
        "logging.enabled", bool, default=False,
        description="Enable or disable logging to a user-specific file."
    )

    USERNAME = ConfigurationKey[str](
        "username", str,
        description="The username for the Fathom client."
    )

    PASSWORD = ConfigurationKey[str](
        "password", str,
        description=(
            "The password for the Fathom client. "
            "Leave empty to be prompted for the password interactively "
            "when using the client."
        )
    )


class ServerConfigurationSection(ConfigurationSectionKey):
    """Definition of configuration keys within the server config section."""

    NAME = ConfigurationKey[str](
        "name", str
    )

    DOMAIN = ConfigurationKey[str](
        "domain", str
    )

    USERNAME = ConfigurationKey[str](
        "username", str
    )

    PASSWORD = ConfigurationKey[str](
        "password", str
    )

    PORT = ConfigurationKey[int](
        "port", int
    )

    LOCATION = ConfigurationKey[str](
        "location", str
    )

    TRANSPORT_SECURE = ConfigurationKey[bool](
        "transport.secure", bool, default=True
    )


class ProjectConfigurationSection(ConfigurationSectionKey):
    """Definition of configuration keys within the project config section."""

    IDENTIFIER = ConfigurationKey[str](
        "id", str
    )

    NAME = ConfigurationKey[str](
        "name", str
    )

    DESCRIPTION = ConfigurationKey[str](
        "description", str
    )

    VERSION = ConfigurationKey[str](
        "version", str
    )

    DOMAIN = ConfigurationKey[str](
        "domain", str
    )

    ASSETS = ConfigurationKey[str](
        "assets", str
    )


class FileFilterConfigurationSection(ConfigurationSectionKey):
    """Definition of config keys within the file filter config section."""

    FILE_TYPE = ConfigurationKey[str](
        "file.type", str
    )

    FILE_NAMES = ConfigurationKey[set](
        "file.names", set
    )

    FILE_EXTENSIONS = ConfigurationKey[set](
        "file.extensions", set
    )

    FILE_PREFIXES = ConfigurationKey[set](
        "file.prefixes", set
    )

    FILE_SIZE_MIN = ConfigurationKey[FileSize](
        "file.size.min", FileSize
    )

    FILE_SIZE_MAX = ConfigurationKey[FileSize](
        "file.size.max", FileSize
    )

    FILE_IGNORE_NONEXISTENT = ConfigurationKey[bool](
        "file.ignore.nonexistent", bool, default=False
    )


class UserConfiguration(ConfigurationDefinition):
    """Definition of the user configuration and its sections.

    These keys are specific to the Fathom client application.
    """

    USER = UserConfigurationSection(
        name="User",
        description=(
            "Definition of the Fathom user to use be a client executed under "
            "the corresponding host system user."
        ),
    )

    SERVER = ServerConfigurationSection(
        name="Server",
        repeatable=True,
        description=(
            "Definitions of servers that can be used by the Fathom client. "
            "May be specified multiple times to define multiple servers. "
            "Projects may refer to these servers by name in their "
            "project configuration."
        ),
    )


class ProjectConfiguration(ConfigurationDefinition):
    """Definition of the project configuration and its sections.

    These keys are specific to the Fathom client application.
    """

    PROJECT = ProjectConfigurationSection(
        name="Project",
        description="Information about the project."
    )

    FILE_FILTER_INCLUDE = FileFilterConfigurationSection(
        name="Filter-Include",
        description=(
            "File filter to include files that match "
            "the specified criteria."
        )
    )

    FILE_FILTER_EXCLUDE = FileFilterConfigurationSection(
        name="Filter-Exclude",
        description=(
            "File filter to exclude files that match "
            "the specified criteria."
        )
    )

    SERVER = ServerConfigurationSection(
        name="Server",
        description=(
            "Specification which server to be used for this project. "
            "You can either specify just the name of the server, which then "
            "refers to the server information as specified in the user "
            "configuration, or you can specify all server information "
            "directly in the project configuration. Individiual server "
            "configuration fields that are also defined in the "
            "user configuration may be overridden "
            "by the project configuration."
        )
    )


@singleton
class ConfigurationManager:
    """Manages Fathom client configuration objects.

    Provides the main API to access and control Fathom configurations
    throughout the client component.
    """

    FILE_NAMES: Final = ("fathom", ".fathom", "docs/fathom", "docs/.fathom")

    FILE_EXTENSIONS: Final = ("config", "cfg")

    def __init__(self):
        """Initializes a new `ConfigurationManager` instance.

        The new instance is able to access the global
        application configuration.
        """
        self._config_user = None
        self._config_project = None
        self._args = None
        self._lock = threading.Lock()

    def load_configs(self, args: "ArgumentsCLI"):
        """Setup functionality for the client configuration.
        
        Args:
            args (ArgumentsCLI): The parsed command line arguments.
        """
        LOG.d(
            "Loading client configuration object in memory. "
            "Config files will be lazy-loaded on demand"
        )
        self._args = args

    def get_user_config(self) -> Configuration:
        """Gets the user configuration.

        Each system user on the host system may have his own configuration
        established in a dedicated configuration file under the user's home
        directory. This method provides access to the configuration read
        from that file.

        Returns:
            Configuration: The user configuration.

        Raises:
            ConfigurationReadException: Or a subclass thereof if the user
                configuration file could not be read.
        """
        with self._lock:
            if self._config_user is None:
                LOG.d(
                    "Lazy-loading user configuration file "
                    "because is it requested now"
                )
                self._config_user = self._load_user_config()

        return self._config_user

    def get_project_config(self) -> Configuration:
        """Gets the configuration pertaining to a specific project.

        Each project on disk has its own configuration established in a
        dedicated configuration file, usually named 'fathom.cfg' located
        either in the project's source root or under a 'docs' subdirectory.
        This method provides access to the configuration read from that file.

        Returns:
            Configuration: The project configuration.

        Raises:
            ConfigurationReadException: Or a subclass thereof if the project
                configuration file could not be read.
        """
        with self._lock:
            if self._config_project is None:
                LOG.d(
                    "Lazy-loading project configuration file "
                    "because is it requested now"
                )
                self._config_project = self._load_project_config()

        return self._config_project

    def _load_user_config(self):
        config_dir = self._get_user_config_base()
        for config_file in self._get_all_file_permutations(("user", "User")):
            config_file = config_dir / File(config_file)
            LOG.d("Trying user configuration file '%s'", config_file)
            if config_file.is_regular_file():
                LOG.d(
                    "Loading found user configuration file '%s'",
                    config_file
                )
                return ConfigurationLoader(
                    UserConfiguration, LOG, enable_validation=True
                ).load(config_file)

        LOG.d(
            "No user configuration file found in known places. "
            "Falling back to empty configuration object with default values"
        )
        return Configuration()

    def _get_user_config_base(self):
        env = SystemEnvironment.instance()
        xdg_config_home = env.get_variable("XDG_CONFIG_HOME")
        if xdg_config_home:
            return File(xdg_config_home)

        home_dir = env.get_home_path()
        if home_dir is None:
            LOG.w(
                "Cannot determine configuration directory. "
                "User home directory not found. "
                "Your system might be misconfigured"
            )
            home_dir = env.get_current_working_directory() # Unlikely fallback

        return File(home_dir) / File(".config") / File(APPLICATION_PROJECT_ID)

    def _load_project_config(self):
        assert self._args is not None
        project_directory = self._args.project_directory
        if not project_directory:
            env = SystemEnvironment.instance()
            project_directory = env.get_current_working_directory()

        project_directory = File(project_directory)
        for config_file in self._get_all_file_permutations(
            ConfigurationManager.FILE_NAMES
        ):
            config_file = project_directory / File(config_file)
            if config_file.is_regular_file():
                LOG.d(
                    "Loading found project configuration from file '%s'",
                    config_file
                )
                return ConfigurationLoader(
                    ProjectConfiguration, LOG, enable_validation=True
                ).load(config_file)

        LOG.w("No project configuration file found")
        return Configuration()

    def _get_all_file_permutations(self, file_names):
        return (
            f"{name}.{ext}"
            for name, ext in itertools.product(
                file_names,
                ConfigurationManager.FILE_EXTENSIONS,
            )
        )
