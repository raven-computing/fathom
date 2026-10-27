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

from typing import TYPE_CHECKING, Optional, Final

from raven.fathom.base import TypeCheck
from raven.fathom.base import Configuration, ConfigurationSection
from raven.fathom.base import URL, URLAuthority
from raven.fathom.base import InputPrompt
from raven.fathom.base.context import APPLICATION_PROJECT_ID
from raven.fathom.client.config import UserConfiguration, ProjectConfiguration
from raven.fathom.client.logging import Logger
from raven.fathom.client.exceptions import InvalidConfigurationException

if TYPE_CHECKING:
    from raven.fathom.client.cli.arguments import AppArgs


LOG = Logger.get()

_SERVER_COMM_VERSION: Final = "v1"


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
        server_name (str): The descriptive name of the server. Can be set.
            May be `None`.
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
        self._server_name = None

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

    @property
    def server_name(self) -> Optional[str]:
        """The descriptive name of the server that this locator points to.

        May be `None`.
        """
        return self._server_name

    @server_name.setter
    def server_name(self, value: Optional[str]):
        if value is not None:
            TypeCheck.require_prop(value, str, "server_name")

        self._server_name = value

    def __str__(self):
        return (
            f"ServerLocator(domain={self._domain}, "
            f"name={self._server_name}, "
            f"port={self._port}, secure={self._secure_connection})"
        )

    def __repr__(self):
        return str(self)


def server_locator_to_url(locator: ServerLocator) -> URL:
    """Obtains a concrete URL from the specified server locator object.

    Args:
        locator (ServerLocator): The server locator for which to get a URL.

    Returns:
        URL: A `URL` object to access the server pointed to
            by the specified `ServerLocator` object.
    """
    url = URL()
    url.scheme = "https" if locator.secure_connection else "http"
    url.authority = URLAuthority(
        hostname=locator.domain,
        port=locator.port
    )
    if locator.location is not None:
        url.path = locator.location

    url.path += f"/{APPLICATION_PROJECT_ID}/{_SERVER_COMM_VERSION}"
    return url


def _load_from_cli_args(args: "AppArgs") -> ServerLocator:
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


def _load_from_user_config_section(
    config: ConfigurationSection
)-> ServerLocator:
    server_name = config.value_of(UserConfiguration.SERVER.NAME)
    if not server_name:
        LOG.e(
            "The server referenced in the user configuration "
            "has no name set"
        )
        raise InvalidConfigurationException(
            "Missing configuration in user config"
        )

    domain = config.value_of(UserConfiguration.SERVER.DOMAIN)
    if domain is None:
        LOG.e(
            "The server referenced in the user configuration "
            "has no domain set"
        )
        LOG.e(
            "Missing configuration key '%s' for server '%s'",
            UserConfiguration.SERVER.DOMAIN.name,
            server_name
        )
        raise InvalidConfigurationException(
            "Missing configuration in user config"
        )

    use_secure_connection = config.value_of(
        UserConfiguration.SERVER.TRANSPORT_SECURE
    )

    server = ServerLocator(domain)
    server.server_name = server_name
    server.secure_connection = (
        use_secure_connection
        if use_secure_connection is not None
        else True
    )
    server.port = config.value_of(UserConfiguration.SERVER.PORT)
    server.location = config.value_of(UserConfiguration.SERVER.LOCATION)
    return server


def _load_from_user_config(config: Configuration)-> ServerLocator:
    server_sections = config.get_repeatable_sections(UserConfiguration.SERVER)
    if len(server_sections) == 0:
        raise InvalidConfigurationException(
            "Missing server configuration. "
            "Specify --server or configure a server in the user config."
        )
    if len(server_sections) == 1:
        return _load_from_user_config_section(server_sections[0])

    sys_in = InputPrompt.instance()
    available_server_names = list(
        filter(
            None,
            [
                section.value_of(UserConfiguration.SERVER.NAME)
                for section in server_sections
            ]
        )
    )
    LOG.i("Which server should be used?")
    selected_name = sys_in.select(available_server_names)
    selected_server_section = [
        section
        for section in server_sections
        if section.value_of(UserConfiguration.SERVER.NAME) == selected_name
    ][0]
    return _load_from_user_config_section(selected_server_section)


def _has_no_server_entry(project: Configuration) -> bool:
    return (
        project.is_empty()
        or not project.has_section(ProjectConfiguration.SERVER)
    )


def _get_project_server_values(
    project: Configuration,
) -> tuple[
    Optional[str],
    Optional[int],
    Optional[str],
    Optional[bool],
]:
    section = project.get_section(ProjectConfiguration.SERVER)
    return (
        section.value_of(ProjectConfiguration.SERVER.DOMAIN, default=None),
        section.value_of(ProjectConfiguration.SERVER.PORT, default=None),
        section.value_of(ProjectConfiguration.SERVER.LOCATION, default=None),
        section.value_of(
            ProjectConfiguration.SERVER.TRANSPORT_SECURE,
            default=None,
        ),
    )


def _find_named_server(
    user: Configuration,
    server_name: str,
) -> Optional[ConfigurationSection]:
    for section in user.get_repeatable_sections(UserConfiguration.SERVER):
        if section.value_of(UserConfiguration.SERVER.NAME) == server_name:
            return section

    return None


def _merge_with_user_server(
    user_server: ConfigurationSection,
    server_name: Optional[str],
    domain: Optional[str],
    port: Optional[int],
    location_path: Optional[str],
    use_secure_connection: Optional[bool],
) -> tuple[Optional[str], Optional[int], Optional[str], Optional[bool]]:
    if domain is None:
        domain = user_server.value_of(UserConfiguration.SERVER.DOMAIN)
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
        use_secure_connection = user_server.value_of(
            UserConfiguration.SERVER.TRANSPORT_SECURE
        )
        use_secure_connection = (
            use_secure_connection
            if use_secure_connection is not None
            else True
        )

    if port is None:
        port = user_server.value_of(UserConfiguration.SERVER.PORT)

    if location_path is None:
        location_path = user_server.value_of(UserConfiguration.SERVER.LOCATION)

    return domain, port, location_path, use_secure_connection


def _load_from_configs(
    user: Configuration,
    project: Configuration
)-> ServerLocator:

    if _has_no_server_entry(project):
        return _load_from_user_config(user)

    server_name = project.value_of(ProjectConfiguration.SERVER.NAME)
    domain, port, location, use_secure_connection = _get_project_server_values(
        project
    )

    if (not server_name
        and domain is None
        and use_secure_connection is None
        and port is None
        and location is None
    ):
        return _load_from_user_config(user)

    selected_server_name = None
    referenced_server_section = None
    if server_name:
        referenced_server_section = _find_named_server(user, server_name)
        if (referenced_server_section is None
            and not any(
                value is not None for value in (
                    domain,
                    use_secure_connection,
                    port,
                    location,
                )
            )
        ):
            LOG.e(
                "The server referenced in the project configuration "
                "cannot be found"
            )
            LOG.e("No server available with name '%s'", server_name)
            raise InvalidConfigurationException("Missing configuration")

    if referenced_server_section is not None:
        selected_server_name = server_name
        domain, port, location, use_secure_connection = (
            _merge_with_user_server(
                referenced_server_section,
                server_name,
                domain,
                port,
                location,
                use_secure_connection,
            )
        )
    elif (
        user.get_repeatable_sections(UserConfiguration.SERVER) and
        (
            domain is None
            or port is None
            or location is None
            or use_secure_connection is None
        )
    ):
        default_server = _load_from_user_config(user)
        selected_server_name = default_server.server_name
        if domain is None:
            domain = default_server.domain
        if use_secure_connection is None:
            use_secure_connection = default_server.secure_connection
        if port is None:
            port = default_server.port
        if location is None:
            location = default_server.location

    if domain is None:
        LOG.e(
            "The server referenced in the project configuration "
            "has no domain set"
        )
        raise InvalidConfigurationException(
            "Missing configuration in user config"
        )

    server = ServerLocator(domain)
    server.server_name = selected_server_name
    server.secure_connection = (
        use_secure_connection
        if use_secure_connection is not None
        else True
    )
    server.port = port
    server.location = location
    return server


def load_server_locator(
    args: "AppArgs",
    user_config: Configuration,
    project_config: Configuration
) -> ServerLocator:
    """Retrieves the server location details.

    This data is searched for in the following order, where a server specified
    via the command line argument takes precedence over present
    configuration files.

    1. Command line arguments
    2. Configuration files

    In the second step, the project configuration file, if not empty,
    is searched for server locator details. The project configuration may
    refer to a specific server by name in its server section, in which case the
    corresponding server information is looked up in the user configuration.
    Any server information specified in the project configuration takes
    precedence over the equivalent entry in the user configuration. So the
    created server locator could reflect the combined configuration of project
    and user configuration.

    If there is no project configuration or it does not specify a server, the
    user configuration is used to determine the server locator details. In that
    case, and if multiple server sections exist in the user configuration, the
    user is prompted to select the desired server. So this method may block
    execution until the user enters a selection.

    If the server location details cannot be determined, an exception
    is raised.

    Args:
        args (AppArgs): The command line arguments. May be empty.
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
