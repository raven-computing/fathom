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
"""Fathom server locators used by clients.

Implements a function to retrieve the details for how to
contact the Fathom server.
"""

from typing import TYPE_CHECKING, Optional

from raven.fathom.base import TypeCheck
from raven.fathom.base import Configuration
from raven.fathom.base import URL
from raven.fathom.client.config import UserConfiguration, ProjectConfiguration
from raven.fathom.client.logging import Logger
from raven.fathom.client.exceptions import InvalidConfigurationException

if TYPE_CHECKING:
    from raven.fathom.client.cli.arguments import ArgumentsCLI


LOG = Logger.get()


class ServerLocator:
    """A locator for Fathom servers.

    A locator is used by clients to find and connect to Fathom servers.

    Attributes:
        domain (str): The domain of the server, e.g. "fathom.example.com".
            Could also be specified by an IP address.
        port (int): The port of the Fathom server. May be `None` to have
            the port chosen automatically by the client.
        location (str): The path location of the Fathom server under the
            given domain. May be `None` if the server is located at
            the root of the domain.
        secure_connection (bool): Indicates whether the connection to
            the Fathom server should be established via a secure connection
            or if potentially insecure connections are allowed.
    """

    def __init__(self, domain: str):
        """Initializes a new `ServerLocator` instance.

        Args:
            domain (str): The domain of the Fathom server.
        """
        TypeCheck.require_arg(domain, str)
        if not domain:
            raise ValueError("Argument 'domain' must not be an empty string")

        self._domain = domain
        self._port = None
        self._location = None
        self._secure_connection = True

    @property
    def domain(self) -> str:
        """The domain of the Fathom server."""
        return self._domain

    @property
    def port(self) -> Optional[int]:
        """The port of the Fathom server.

        May be `None` if no explicit port is specified.
        """
        return self._port

    @port.setter
    def port(self, value: Optional[int]):
        if value is not None:
            TypeCheck.require_prop(value, int, "port")

        self._port = value

    @property
    def location(self) -> Optional[str]:
        """The path location of the Fathom server under the given domain."""
        return self._location

    @location.setter
    def location(self, value: Optional[str]):
        """Sets the path location to the Fathom server."""
        if value is not None:
            TypeCheck.require_prop(value, str, "location")

        self._location = value

    @property
    def secure_connection(self) -> bool:
        """Indicates whether communication with the Fathom server should be
        established via secure network connections.

        A connection is secure by default but can be set to `False` to allow
        potentially insecure connections. This is useful for testing or during
        development. It is generally not recommended to disable secure
        connections in production environments, unless you have a specific
        reason to do so and understand the security implications.
        """
        return self._secure_connection

    @secure_connection.setter
    def secure_connection(self, value: bool):
        TypeCheck.require_prop(value, bool, "secure_connection")
        self._secure_connection = value

    def __str__(self):
        return (
            f"ServerLocator(domain={self._domain}, "
            f"port={self._port}, secure={self._secure_connection})"
        )

    def __repr__(self):
        return str(self)


def _load_from_cli_args(args: "ArgumentsCLI") -> ServerLocator:
    url = URL(args.server)
    domain = url.authority.hostname
    if not url.scheme in ("http", "https"):
        LOG.e("Unsupported communication protocol '%s'", url.scheme)
        LOG.e("Only HTTP(S) is supported")
        raise InvalidConfigurationException("Not a valid server location")

    use_secure_connection = url.scheme == "https"
    port = url.authority.port
    location_path = url.path or None
    server = ServerLocator(domain)
    server.secure_connection = use_secure_connection
    server.port = port
    server.location = location_path
    return server


def _load_from_configs(
    user: Configuration,
    project: Configuration
)-> ServerLocator:

    server_name = project.get_required_value(ProjectConfiguration.SERVER.NAME)

    domain = project.value_of(ProjectConfiguration.SERVER.DOMAIN)
    use_secure_connection = user.value_of(
        ProjectConfiguration.SERVER.TRANSPORT_SECURE
    )
    port = user.value_of(ProjectConfiguration.SERVER.PORT)
    location_path = user.value_of(ProjectConfiguration.SERVER.LOCATION)

    referenced_server_section = None
    for section in user.get_repeatable_sections(UserConfiguration.SERVER):
        if section.value_of(UserConfiguration.SERVER.NAME) == server_name:
            referenced_server_section = section

    if referenced_server_section is None:
        LOG.e(
            "The server referenced in the project configuration "
            "cannot be found"
        )
        LOG.e("No server available with name '%s'", server_name)
        raise InvalidConfigurationException("Missing configuration")

    if domain is None:
        domain = referenced_server_section.value_of(
            UserConfiguration.SERVER.DOMAIN
        )
        if domain is None:
            LOG.e(
                "The server referenced in the project configuration "
                "has no domain set within the user configuration"
            )
            LOG.e(
                "Missing configuration key '%s' for server '%s'",
                UserConfiguration.SERVER.DOMAIN.name,
                server_name
            )
            raise InvalidConfigurationException(
                "Missing configuration in user config"
            )

    if use_secure_connection is None:
        use_secure_connection = referenced_server_section.value_of(
            UserConfiguration.SERVER.TRANSPORT_SECURE
        ) or True

    if port is None:
        port = referenced_server_section.value_of(
            UserConfiguration.SERVER.PORT
        )

    if location_path is None:
        location_path = referenced_server_section.value_of(
            UserConfiguration.SERVER.LOCATION
        )

    server = ServerLocator(domain)
    server.secure_connection = use_secure_connection
    server.port = port
    server.location = location_path
    return server


def load_server_locator(
    args: "ArgumentsCLI",
    user_config: Configuration,
    project_config: Configuration
) -> ServerLocator:
    """Retrieves the server location details.

    Args:
        args (ArgumentsCLI): The command line arguments. May be empty.
        user_config (Configuration): The user configuration. May be empty.
        project_config (Configuration): The project configuration.
            May be empty.

    Returns:
        ServerLocator: The loaded server location details.

    Raises:
        InvalidConfigurationException: If there is a configuration issue.
    """
    if args.server:
        return _load_from_cli_args(args)

    return _load_from_configs(user_config, project_config)


def load_management_server_locator(
    args: "ArgumentsCLI",
    user_config: Configuration,
) -> ServerLocator:
    """Retrieves the server location details for management commands.

    Args:
        args (ArgumentsCLI): The command line arguments. May be empty.
        user_config (Configuration): The user configuration. May be empty.

    Returns:
        ServerLocator: The loaded server location details.

    Raises:
        InvalidConfigurationException: If there is a configuration issue.
    """
    if args.server:
        return _load_from_cli_args(args)

    server_sections = user_config.get_repeatable_sections(
        UserConfiguration.SERVER
    )
    if len(server_sections) == 0:
        raise InvalidConfigurationException(
            "Missing server configuration. "
            "Specify --server or configure a server in the user config."
        )

    section = server_sections[0]
    domain = section.value_of(UserConfiguration.SERVER.DOMAIN)
    if not domain:
        raise InvalidConfigurationException(
            "Missing server domain in user configuration."
        )

    server = ServerLocator(domain)
    server.secure_connection = section.value_of(
        UserConfiguration.SERVER.TRANSPORT_SECURE
    ) or False
    server.port = section.value_of(UserConfiguration.SERVER.PORT)
    server.location = section.value_of(UserConfiguration.SERVER.LOCATION)
    return server
