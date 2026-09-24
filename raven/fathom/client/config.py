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
from raven.fathom.base import ApplicationContext, ApplicationMode
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
        description=(
            "The username to use when authenticating to the Fathom server "
            "and there is no username set in the specific server "
            "configuration entry."
        )
    )

    PASSWORD = ConfigurationKey[str](
        "password", str,
        description=(
            "The password to use when authenticating to the Fathom server "
            "and there is no password set in the specific server "
            "configuration entry. Leave empty to be prompted for the password "
            "interactively when using the client."
        )
    )


class ServerConfigurationSection(ConfigurationSectionKey):
    """Definition of configuration keys within the server config section."""

    NAME = ConfigurationKey[str](
        "name", str,
        description=(
            "The name of the server by which a project can refer to it "
            "in its configuration.")
    )

    DOMAIN = ConfigurationKey[str](
        "domain", str,
        description="The DNS domain or IP address of the server."
    )

    USERNAME = ConfigurationKey[str](
        "username", str,
        description="The username to use when connecting to the server."
    )

    PASSWORD = ConfigurationKey[str](
        "password", str,
        description="The password to use when authenticating to the server."
    )

    PORT = ConfigurationKey[int](
        "port", int,
        description="The port of the server to connect to."
    )

    LOCATION = ConfigurationKey[str](
        "location", str,
        description=(
            "The location of the server under the given domain. "
            "This is a path on the remote host where the Fathom server "
            "can be accessed."
        )
    )

    TRANSPORT_SECURE = ConfigurationKey[bool](
        "transport.secure", bool, default=True,
        description=(
            "Whether to use a cryptographically secure networking protocol "
            "when connecting to the server."
        )
    )


class ProjectConfigurationSection(ConfigurationSectionKey):
    """Definition of configuration keys within the project config section."""

    IDENTIFIER = ConfigurationKey[str](
        "id", str,
        description=(
            "The unique identifier of the project. This must match the global "
            "identifier of the project as it is known to the Fathom server."
        )
    )

    NAME = ConfigurationKey[str](
        "name", str,
        description="The human-readable name of the project."
    )

    DESCRIPTION = ConfigurationKey[str](
        "description", str,
        description="A brief description of the project."
    )

    VERSION = ConfigurationKey[str](
        "version", str,
        description="The version of the project."
    )

    DOMAIN = ConfigurationKey[str](
        "domain", str,
        description=(
            "The domain associated with the project, or where "
            "the documentation can be found. For example: 'docs.example.com'"
        )
    )

    ASSETS = ConfigurationKey[str](
        "assets", str,
        description=(
            "The location of the project's assets. This is a path in the "
            "local filesystem where the files that should be "
            "included in a deployment are located."
        )
    )


class FileFilterConfigurationSection(ConfigurationSectionKey):
    """Definition of config keys within the file filter config section."""

    FILE_TYPE = ConfigurationKey[str](
        "file.type", str,
        description=(
            "The type of the file to filter for. Must be one of "
            "['any', 'regular_file', 'directory', 'symlink', 'nonexistent']"
        )
    )

    FILE_NAMES = ConfigurationKey[set](
        "file.names", set,
        description=(
            "The set of file names to filter for, specified as "
            "a set of strings. For example: {'myfile.txt', 'index.html'}"
        )
    )

    FILE_EXTENSIONS = ConfigurationKey[set](
        "file.extensions", set,
        description=(
            "The set of file extensions to filter for, specified as "
            "a set of strings. For example: {'.py', '.txt'}"
        )
    )

    FILE_PREFIXES = ConfigurationKey[set](
        "file.prefixes", set,
        description=(
            "The set of file prefixes to filter for, specified as "
            "a set of strings. A prefix is matched against the beginning "
            "of the file path. For example: {'this/that', 'res/unused'}"
        )
    )

    FILE_SIZE_MIN = ConfigurationKey[FileSize](
        "file.size.min", FileSize,
        description=(
            "The minimum size of files allowed. "
            "Must be specified as a number with a unit. "
            "For example: '10MB', '500KB'."
        )
    )

    FILE_SIZE_MAX = ConfigurationKey[FileSize](
        "file.size.max", FileSize,
        description=(
            "The maximum size of files allowed. "
            "Must be specified as a number with a unit. "
            "For example: '10MB', '500KB'."
        )
    )

    FILE_IGNORE_NONEXISTENT = ConfigurationKey[bool](
        "file.ignore.nonexistent", bool, default=False,
        description=(
            "Indicates whether to ignore files which do not actually "
            "exist in the filesystem."
        )
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
        self._lock = threading.RLock()
        self._mode = None
        self._cache_enabled = None

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

            self._check_mode()
            if self._config_user is None or not self._cache_enabled:
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

            self._check_mode()
            if self._config_project is None or not self._cache_enabled:
                self._config_project = self._load_project_config()

        return self._config_project

    def has_user_config_file(self) -> bool:
        """Checks whether a user configuration file exists.

        Returns:
            bool: `True` if the configuration file exists.
        """
        return self.find_user_config_file() is not None

    def create_default_user_config_file(self) -> File:
        """Creates the default user configuration file.

        Overwrites an existing file if it already exists.

        Returns:
            File: The user configuration file path.

        Raises:
            ConfigurationWriteException: If the file cannot be written.
        """
        self._check_mode()
        config_file = self.get_default_user_config_file()
        config_file.get_parent_directory().create_directory_tree()
        ConfigurationLoader(UserConfiguration).store(
            UserConfiguration.default_configuration(),
            config_file,
        )
        return config_file

    def has_project_config_file(self) -> bool:
        """Checks whether a project configuration file exists.

        Returns:
            bool: `True` if the configuration file exists.
        """
        return self.find_project_config_file() is not None

    def find_user_config_file(self) -> File | None:
        """Finds the first applicable user configuration file.

        Returns:
            File: The discovered user configuration file, or `None`
                if no applicable file exists.
        """
        with self._lock:
            self._check_mode()
            config_dir = self._get_user_config_base()
            for config_file in self._get_all_file_permutations(
                ("user", "User")
            ):
                candidate = config_dir / File(config_file)
                LOG.d("Trying user configuration file '%s'", candidate)
                if candidate.is_regular_file():
                    return candidate

        return None

    def find_project_config_file(self) -> File | None:
        """Finds the first applicable project configuration file.

        Returns:
            File: The discovered project configuration file, or `None`
                if no applicable file exists.
        """
        with self._lock:
            config_dir = self.get_default_project_config_file()
            config_dir = config_dir.get_parent_directory()
            for config_file in self._get_all_file_permutations(
                ConfigurationManager.FILE_NAMES
            ):
                candidate = config_dir / File(config_file)
                if candidate.is_regular_file():
                    return candidate

        return None

    def create_default_project_config_file(self) -> File:
        """Creates the default project configuration file.

        Overwrites an existing file if it already exists.

        Returns:
            File: The project configuration file path.

        Raises:
            ConfigurationWriteException: If the file cannot be written.
        """
        config_file = self.get_default_project_config_file()
        ConfigurationLoader(ProjectConfiguration).store(
            ProjectConfiguration.default_configuration(),
            config_file,
        )
        return config_file

    def get_default_user_config_file(self) -> File:
        """Gets the default user configuration file location.

        Returns:
            File: The default user configuration file path.
        """
        self._check_mode()
        return self._get_user_config_base() / File("user.cfg")

    def get_default_project_config_file(self) -> File:
        """Gets the default project configuration file location.

        Returns:
            File: The default project configuration file path.
        """
        assert self._args is not None
        project_directory = self._args.project_directory
        if not project_directory:
            env = SystemEnvironment.instance()
            project_directory = env.get_current_working_directory()

        return File(project_directory) / File("fathom.cfg")

    def _check_mode(self):
        if self._mode is None:
            ctx = ApplicationContext.instance()
            self._mode = ctx.get_application_mode()
            self._cache_enabled = self._mode == ApplicationMode.PRODUCTION

    def _load_user_config(self):
        config_file = self.find_user_config_file()
        if config_file is not None:
            LOG.d(
                "Loading found user configuration file '%s'",
                config_file
            )
            return ConfigurationLoader(
                UserConfiguration, LOG, enable_validation=True
            ).load(config_file)

        if self._mode == ApplicationMode.DEVELOPMENT:
            config_dir = self._get_user_config_base()
            LOG.d("[DEVELOPMENT MODE] Storing user config file for testing")
            devel_config = self._create_default_devel_user_config()
            config_dir.create_directory_tree()
            ConfigurationLoader(UserConfiguration).store(
                devel_config,
                config_dir / File("user.cfg")
            )
        else:
            LOG.d(
                "No user configuration file found in known places. "
                "Falling back to empty configuration object "
                "with default values"
            )

        return Configuration()

    def _create_default_devel_user_config(self):
        devel_config = UserConfiguration.default_configuration()
        server = devel_config.get_section(UserConfiguration.SERVER)
        server[UserConfiguration.SERVER.NAME] = (
                "Local Development Server"
            )
        server[UserConfiguration.SERVER.DOMAIN] = "localhost"
        server[UserConfiguration.SERVER.PORT] = 8080
        server[UserConfiguration.SERVER.TRANSPORT_SECURE] = False
        devel_config[UserConfiguration.USER.USERNAME] = "alpha"
        devel_config[UserConfiguration.USER.PASSWORD] = "alpha"
        return devel_config

    def _get_user_config_base(self):
        if self._mode == ApplicationMode.DEVELOPMENT:
            ctx = ApplicationContext.instance()
            home_dir = ctx.get_working_directory() / File("user")
            LOG.d(
                "[DEVELOPMENT MODE] Overriding user's home directory "
                "to confined directory in build tree"
            )
        else:
            env = SystemEnvironment.instance()
            xdg_config_home = env.get_variable("XDG_CONFIG_HOME")
            if xdg_config_home:
                home_dir = File(xdg_config_home)
            else:
                home_dir = env.get_home_path()
                if home_dir is None:
                    LOG.w(
                        "Cannot determine configuration directory. "
                        "User home directory not found. "
                        "Your system might be misconfigured"
                    )
                    # Unlikely fallback
                    home_dir = env.get_current_working_directory()

        return File(home_dir) / File(".config") / File(APPLICATION_PROJECT_ID)

    def _load_project_config(self):
        config_file = self.find_project_config_file()
        if config_file is not None:
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
