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
"""Connection API from the client to the server."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from raven.fathom.base import ServerConnection
from raven.fathom.base import Interaction
from raven.fathom.base import ClientRequest, ClientAuthentication
from raven.fathom.base import TransmissionException
from raven.fathom.base import ClientDeploymentIntent
from raven.fathom.base import DeploymentAuthorization
from raven.fathom.base import Package
from raven.fathom.base import DeploymentMessage
from raven.fathom.client.logging import Logger
from raven.fathom.client.exceptions import FathomClientException

if TYPE_CHECKING:
    from raven.fathom.client.locator import ServerLocator


LOG = Logger.get()


class ServerConnectionException(FathomClientException):
    """A failed connection or communication with the server."""


@dataclass
class ServerInfo:
    """Information provided by the remote server about its state
    and capabilities.
    """

    server_agent: Optional[str] = field(default=None)

    app_version: str = field(default="")


class Server:
    """Higher-level API to interact with a Fathom server.

    Instances of `Server` can be used by clients to establish a connection
    to a potentially remote Fathom server and communicate with it.
    """

    def __init__(
        self,
        location: "ServerLocator",
        authentication: Optional[ClientAuthentication]
    ):
        """Initializes a new `Server` instance.

        The instance can be used to communicate with the potentially remote
        Fathom server using the specified connection parameters.

        Args:
            location (ServerLocator): The connection location of the server.
            authentication (ClientAuthentication): The authentication
                parameters of the client. May be `None` if no authentication
                is required.
        """
        self._location = location
        self._client_authentication = authentication

    def request_server_info(self):
        """Requests state information from the server.

        Returns:
            ServerInfo: The information provided by the server.

        Raises:
            ServerConnectionException: If a connection to the server cannot
                be established or if the server responds incorrectly or in
                an unexpected way.
        """
        request = ClientRequest(Interaction.QUERY_SERVER_INFO)
        request.authentication = self._client_authentication

        LOG.v("Requesting general information from server")
        response = self._send(request)

        server_info_map = response.server_info
        if server_info_map is None:
            raise ServerConnectionException(
                "Server response does not contain expected server info map"
            )

        server_info = ServerInfo()
        server_info.server_agent = server_info_map.get("server_agent")
        server_info.app_version = server_info_map.get("app_version", "")
        return server_info

    def request_deployment(
        self,
        intent: ClientDeploymentIntent
    ) -> DeploymentAuthorization:
        """Sends a deployment intent to the server.

        Args:
            intent (ClientDeploymentIntent): The information to be sent
                to the server to have the client signal that it wants to
                deploy a package.

        Returns:
            DeploymentAuthorization: The authorization response sent by the
                server in response to the specified deployment intent.

        Raises:
            ServerConnectionException: If a connection to the server cannot
                be established or if the server responds incorrectly or in
                an unexpected way.
        """
        request = ClientRequest(Interaction.REQUEST_DEPLOYMENT)
        request.authentication = self._client_authentication
        request.deployment_intent = intent

        LOG.v("Requesting deployment authorization from server")
        response = self._send(request)
        authorization = response.deployment_authorization
        if authorization is None:
            raise ServerConnectionException(
                "Server response does not contain expected "
                "deployment authorization"
            )

        return authorization

    def transact_deployment(
        self,
        authorization: DeploymentAuthorization,
        package: Package
    ) -> DeploymentMessage:
        """Sends a deployment transaction with the given authorization to
        the server in order to have the given package deployed.

        Args:
            authorization (DeploymentAuthorization): The deployment
                authorization previously granted by the server.
            package (Package): The resource package to deploy.

        Returns:
            DeploymentMessage: The deployment response of the server.

        Raises:
            ServerConnectionException: If a connection to the server cannot
                be established or if the server responds incorrectly or in
                an unexpected way.
        """
        request = ClientRequest(Interaction.TRANSACT_DEPLOYMENT)
        request.authentication = self._client_authentication
        request.deployment_authorization = authorization
        request.package = package

        LOG.v("Sending deployment transaction to server")
        response = self._send(request)
        message = response.deployment_message
        if message is None:
            message = DeploymentMessage(
                is_successful=False,
                message="Internal server error",
            )

        return message

    def _send(self, request):
        try:
            return ServerConnection.instance(self._location).process(request)
        except TransmissionException as ex:
            raise ServerConnectionException(
                "Could not establish a connection to the server"
            ) from ex
