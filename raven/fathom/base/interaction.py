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
"""Contains classes used in interactions between Fathom clients and servers.

An interaction between a Fathom client and a server follows a request-response
pattern. A client creates a request object, modeled by the `ClientRequest` data
class, and sends it to the server. The server processes the request and returns
a response object, modeled by the `ServerResponse` data class. The response may
contain errors or warnings, which are represented by the `ResponseMessage`
data class.

This module also declares the `ServerConnection` interface, which abstracts the
process of sending and receiving requests and responses between Fathom clients
and servers. A simple request-response mechanism is used. A client sends a
request and waits for the response of the server. In practice, an interaction
between a client and a server will most likely be carried out over a network
connection using the HTTP protocol. However, this is an implementation detail.
It is only specified as a component interface, that both the client and server
component must implement the `ServerConnection` interface class and that when
the client code calls the `process()` method, the server will have its method
implementation called with an equivalent request object as provided by the
client. In the same manner, the response returned by the `process()` method of
the server implementation must be propagated losslessly as the return value
of the `process()` method in the client implementation.
"""

from enum import StrEnum, IntEnum
from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Optional, MutableSequence

from raven.fathom.base.typing import Interface
from raven.fathom.base.decorators import inject
from raven.fathom.base.authentication import ClientAuthentication
from raven.fathom.base.user import User
from raven.fathom.base.project import Project
from raven.fathom.base.package import Package
from raven.fathom.base.deployment import ClientDeploymentIntent
from raven.fathom.base.deployment import DeploymentAuthorization
from raven.fathom.base.deployment import DeploymentMessage
from raven.fathom.base.exceptions import FathomBaseException


class InteractionException(FathomBaseException):
    """Base class for all interaction-related exceptions."""


class TransmissionException(InteractionException):
    """A failed client-server-transmission.

    Raised when the interaction between a Fathom client and server fails
    due to transmission errors. For example, an interaction fails with a
    transmission error when the client cannot reach the server over
    the network. Semantically, an interaction never took place because the
    transmission of that interaction did not succeed.

    Is primarily used by the `ServerConnection` interface.
    """


class ProcessingException(InteractionException):
    """A failed server processing.

    Raised when the interaction between a Fathom client and server fails
    due to processing errors. For example, an interaction fails with a
    processing error when the server cannot process the request of the
    client due to an internal error. Semantically, an interaction took place
    because the request was successfully transmitted to the server, but the
    server failed to fully process it.

    Is primarily used by the `ServerConnection` interface.
    """


class Interaction(StrEnum):
    """The actions that a client can do with a server."""

    QUERY_SERVER_INFO = "server-info"

    REQUEST_DEPLOYMENT = "deploy-request"

    TRANSACT_DEPLOYMENT = "deploy-transaction"

    CREATE_USER = "user-create"

    SETUP_USER = "user-setup"

    LIST_USERS = "user-list"

    DELETE_USER = "user-delete"


@dataclass
class ClientRequest:
    """A request made by a client to a server.

    Attributes:
        action (Interaction): The action requested by the client.
        authentication (ClientAuthentication): The authentication details of
            the client, if any.
        user (User): The user context of the request, if applicable.
        project (Project): The optional project context for the request,
            if applicable.
        deployment_intent (ClientDeploymentIntent): The optional deployment
            intent associated with the request, if applicable.
        deployment_authorization (DeploymentAuthorization): The authorization
            details for a requested and already ganted deployment, if required.
        package (Package): The package involved in a deployment, if any.
        managed_user (User): The user to be created, set up, listed, or
            deleted, if applicable.
    """

    action: Interaction = field(
        init=True,
    )

    authentication: Optional[ClientAuthentication] = field(
        init=False,
        default=None,
    )

    user: Optional[User] = field(
        init=False,
        default=None,
    )

    project: Optional[Project] = field(
        init=False,
        default=None,
    )

    deployment_intent: Optional[ClientDeploymentIntent] = field(
        init=False,
        default=None,
    )

    deployment_authorization: Optional[DeploymentAuthorization] = field(
        init=False,
        default=None,
    )

    package: Optional[Package] = field(
        init=False,
        default=None,
    )

    managed_user: Optional[User] = field(
        init=False,
        default=None,
    )


class ResponseCode(IntEnum):
    """Enumerates numeric response codes of message in server responses."""

    INCOMPLETE_REQUEST = 3

    INTERNAL_ERROR = 4

    NO_PRODUCTION_USE = 5

    NOT_AUTHENTICATED = 6

    NOT_FOUND = 7

    CLIENT_VERSION_NOT_SUPPORTED = 8

    MISSING_AUTHORIZATION = 1

    AUTHORIZATION_DENIED = 2


@dataclass
class ResponseMessage:
    """Represents a message, for example an error or a warning, within a
    server response.

    Attributes:
        code (ResponseCode): The code indicating the type or category of
            the response message.
        text (str): The human-readable message text.
    """

    code: ResponseCode

    text: str


@dataclass
class ServerResponse:
    """A response provided by a server to a client.

    Attributes:
        action (Interaction): The action that the server is responding to.
            Should match the request action.
        errors (MutableSequence[ResponseMessage]): A sequence of error
            messages. An error indicates a failure or refusal of the server to
            fulfill the client's request.
        warnings (MutableSequence[ResponseMessage]): A sequence of warning
            messages. A warning indicates a circumstance that the server wants
            the client to take note of.
        deployment_authorization (DeploymentAuthorization): An optional
            deployment authorization object, in response to a deployment
            request.
        deployment_message (DeploymentMessage): An optional deployment message,
            detailing the result of an executed deployment.
        managed_users (list[User]): An optional list of managed users, in
            response to user management requests.
    """

    action: Interaction = field(
        init=True,
    )

    errors: MutableSequence[ResponseMessage] = field(
        init=False,
        default_factory=list,
    )

    warnings: MutableSequence[ResponseMessage] = field(
        init=False,
        default_factory=list,
    )

    server_info: Optional[dict] = field(
        init=False,
        default=None,
    )

    deployment_authorization: Optional[DeploymentAuthorization] = field(
        init=False,
        default=None,
    )

    deployment_message: Optional[DeploymentMessage] = field(
        init=False,
        default=None,
    )

    managed_users: Optional[list[User]] = field(
        init=False,
        default=None,
    )

    def has_errors(self) -> bool:
        """Indicates whether the response contains any errors.

        Returns:
            bool: `True` if this response contains errors, `False` if it has
                no errors.
        """
        return len(self.errors) > 0

    def add_error(self, error: ResponseMessage):
        """Adds an error message to the response.

        Args:
            error (ResponseMessage): The error message to add to the response.
        """
        self.errors.append(error)

    def has_warnings(self) -> bool:
        """Indicates whether the response contains any warnings.

        Returns:
            bool: `True` if this response contains warnings, `False` if it has
                no warnings.
        """
        return len(self.warnings) > 0

    def add_warning(self, warning: ResponseMessage):
        """Adds a warning message to the response.

        Args:
            warning (ResponseMessage): The warning message to add to the
                response.
        """
        self.warnings.append(warning)


@inject
class ServerConnection(Interface):
    """Interface for a single client-request server-response interaction."""

    @abstractmethod
    def process(self, request: ClientRequest) -> ServerResponse:
        """Sends the specified client request to the server and waits for
        its response.

        Args:
            request (ClientRequest): The request of the client to send.

        Returns:
            ServerResponse: The response of the server to the made request.

        Raises:
            TransmissionException: If the connection cannot be established,
                i.e. the client request cannot be successfully transmitted.
                This is the client-side error type of a failed interaction.
            ProcessingException: If the server cannot process the transmitted
                request. This is the server-side error type of a
                failed interaction.
            InteractionException: Base error type for
                all interaction-related errors.
        """
