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
"""Server configuration definitions.

The primary API is provided by the `ConfigurationManager` class. It can be
directly instantiated and provides methods to obtain `Configuration` objects
which store various global application configuration values.
"""

import itertools
import threading

from typing import TYPE_CHECKING, Final

from raven.fathom.base import Configuration, ConfigurationSection
from raven.fathom.base import ConfigurationDefinition
from raven.fathom.base import ConfigurationKey, ConfigurationSectionKey
from raven.fathom.base import ConfigurationLoader
from raven.fathom.base import ConfigurationWriteException
from raven.fathom.base import File, FileSize, FileSizeUnit
from raven.fathom.base import ApplicationContext
from raven.fathom.base.decorators import singleton
from raven.fathom.server.logging import Logger
from raven.fathom.server.defaults import DEFAULT_SERVER_PORT

if TYPE_CHECKING:
    from raven.fathom.server.cli import AppArgs


LOG = Logger.get()


class ServerConfigurationSection(ConfigurationSectionKey):
    """Enumeration of concrete server configuration keys."""

    DEBUG_MODE_ENABLED = ConfigurationKey[bool](
        "debug.mode.enabled", bool, default=False,
        description="Wether to enable the debug mode."
    )

    DEPLOYMENT_STAGING_DIRECTORY = ConfigurationKey[File](
        "deployment.staging.directory", File, default=File("staging"),
        description=(
            "The path to the directory where all files for the staging area "
            "should be placed. If specified as a relative path, then it is "
            "interpreted as relative to the Fathom server working directory."
        )
    )

    DEPLOYMENT_SITE_DIRECTORY = ConfigurationKey[File](
        "deployment.site.directory", File, default=File("site"),
        description=(
            "The path to the directory where all committed files should "
            "be deployed to. If specified as a relative path, then it is "
            "interpreted as relative to the Fathom server working directory."
        )
    )

    ADDRESS_LISTEN = ConfigurationKey[str](
        "address.listen", str, default="0.0.0.0",
        description=(
            "The hostname or IP address the server should listens on."
            "By default, the server listens on "
            "any active interface (INADDR_ANY)"
        )
    )

    PORT_LISTEN = ConfigurationKey[int](
        "port.listen", int, default=DEFAULT_SERVER_PORT,
        description="The network port the server should listens on. "
                   f"The default is {DEFAULT_SERVER_PORT}."
    )

    PORT_CHECK_BIND = ConfigurationKey[bool](
        "port.check.bind", bool, default=True,
        description="Whether to explicitly test that the server "
                    "can bind to the port."
    )

    THREAD_POOL_SIZE = ConfigurationKey[int](
        "thread_pool.size", int, default=10,
        description=(
            "The number of worker threads that should be started "
            "by the server to serve incoming requests."
        )
    )

    ENABLE_GZIP_COMPRESSION = ConfigurationKey[bool](
        "compression.gzip.enabled", bool, default=False,
        description="Whether to enable GZIP compression of response bodies."
    )

    MAX_REQUEST_HEADER_SIZE = ConfigurationKey[FileSize](
        "request_header.size.max", FileSize,
        default=FileSize(2, FileSizeUnit.MEGABYTE),
        description="The maximum size allowable in request headers."
    )

    MAX_REQUEST_BODY_SIZE = ConfigurationKey[FileSize](
        "request_body.size.max", FileSize,
        default=FileSize(200, FileSizeUnit.MEGABYTE),
        description="The maximum size allowable in request bodies."
    )


class ServerConfiguration(ConfigurationDefinition):
    """Enumeration of known configuration section keys.

    These keys are specific to the Fathom server application.
    """

    SERVER = ServerConfigurationSection("Server")


@singleton
class ConfigurationManager:
    """Manages Fathom server configuration objects.

    Provides the main API to access and control Fathom configurations
    throughout the server component.
    """

    FILE_NAMES: Final = ("fathom", "app")

    FILE_EXTENSIONS: Final = ("config", "cfg")

    def __init__(self):
        """Initializes a new `ConfigurationManager` instance.

        The new instance is able to access the global
        application configuration.
        """
        self._config_app = None
        self._args = None
        self._lock = threading.Lock()

    def load_configs(self, args: "AppArgs"):
        """Setup functionality for the server configuration.
        
        Args:
            args (AppArgs): The parsed command line arguments.
        """
        LOG.d(
            "Loading server configuration object in memory. "
            "Config files will be lazy-loaded on demand"
        )
        self._args = args

    def get_server_config(self) -> Configuration:
        """Gets the server application configuration.

        Returns:
            Configuration: The app configuration.

        Raises:
            ConfigurationReadException: Or a subclass thereof if the user
                configuration file could not be read.
        """
        with self._lock:
            if self._config_app is None:
                LOG.d(
                    "Lazy-loading server app configuration file "
                    "because is it requested now"
                )
                self._config_app = self._load_server_config()

        return self._config_app

    def _load_server_config(self):
        config_dir = ApplicationContext.instance().get_working_directory()
        for config_file in self._get_all_file_permutations(
            ConfigurationManager.FILE_NAMES
        ):
            config_file = config_dir / File(config_file)
            LOG.d("Trying server configuration file '%s'", config_file)
            if config_file.is_regular_file():
                LOG.d(
                    "Loading found server configuration file '%s'",
                    config_file
                )
                return ConfigurationLoader(
                    ServerConfiguration,
                    LOG,
                    enable_validation=True,
                ).load(config_file)

        LOG.d(
            "No server configuration file found in known places. "
            "Falling back to empty configuration object with default values"
        )
        default_config = Configuration()
        server_section = ConfigurationSection(ServerConfiguration.SERVER)
        self._init_default_config(server_section)
        default_config.add_section(server_section)
        self._store_default_config(config_dir, default_config)
        return default_config

    def _store_default_config(self, config_dir, default_config):
        if self._args is not None and self._args.create_default_config:
            config_file = config_dir / File("fathom.cfg")
            if not config_file.exists():
                LOG.i("Storing server configuration file with default values.")
                LOG.i(
                    "You can use the following file "
                    "to configure the server application:"
                )
                LOG.i("File: '%s'", config_file)

            try:
                ConfigurationLoader(
                    ServerConfiguration,
                    LOG,
                ).store(default_config, config_file)
            except ConfigurationWriteException as ex:
                LOG.e("Failed to write default server configuration file.")
                LOG.e(
                    "An error has occurred while trying to store file '%s'",
                    config_file
                )
                LOG.e("%s", ex)

    def _get_all_file_permutations(self, file_names):
        return (
            f"{name}.{ext}"
            for name, ext in itertools.product(
                file_names,
                ConfigurationManager.FILE_EXTENSIONS,
            )
        )

    def _init_default_config(self, server_section):
        server_section.set_value(
            ServerConfiguration.SERVER.DEBUG_MODE_ENABLED,
            ServerConfiguration.SERVER.DEBUG_MODE_ENABLED.default_value
        )
        server_section.set_value(
            ServerConfiguration.SERVER.DEPLOYMENT_STAGING_DIRECTORY,
            ServerConfiguration.SERVER.DEPLOYMENT_STAGING_DIRECTORY
            .default_value
        )
        server_section.set_value(
            ServerConfiguration.SERVER.DEPLOYMENT_SITE_DIRECTORY,
            ServerConfiguration.SERVER.DEPLOYMENT_SITE_DIRECTORY
            .default_value
        )
        server_section.set_value(
            ServerConfiguration.SERVER.ADDRESS_LISTEN,
            ServerConfiguration.SERVER.ADDRESS_LISTEN.default_value
        )
        server_section.set_value(
            ServerConfiguration.SERVER.PORT_LISTEN,
            ServerConfiguration.SERVER.PORT_LISTEN.default_value
        )
        server_section.set_value(
            ServerConfiguration.SERVER.PORT_CHECK_BIND,
            ServerConfiguration.SERVER.PORT_CHECK_BIND.default_value
        )
        server_section.set_value(
            ServerConfiguration.SERVER.ENABLE_GZIP_COMPRESSION,
            ServerConfiguration.SERVER.ENABLE_GZIP_COMPRESSION.default_value
        )
        server_section.set_value(
            ServerConfiguration.SERVER.THREAD_POOL_SIZE,
            ServerConfiguration.SERVER.THREAD_POOL_SIZE.default_value
        )
        server_section.set_value(
            ServerConfiguration.SERVER.MAX_REQUEST_HEADER_SIZE,
            ServerConfiguration.SERVER.MAX_REQUEST_HEADER_SIZE.default_value
        )
        server_section.set_value(
            ServerConfiguration.SERVER.MAX_REQUEST_BODY_SIZE,
            ServerConfiguration.SERVER.MAX_REQUEST_BODY_SIZE.default_value
        )
