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

from dataclasses import dataclass, field, fields
from collections.abc import Sized
from typing import TYPE_CHECKING, Optional, TypeVar, Generic

from raven.fathom.base import ServerInteraction
from raven.fathom.base import Interaction
from raven.fathom.base import ClientRequest, ClientAuthentication
from raven.fathom.base import ServerResponse, ResponseCode
from raven.fathom.base import TransmissionException, ProcessingException
from raven.fathom.base import InteractionException
from raven.fathom.base import ClientDeploymentIntent
from raven.fathom.base import DeploymentAuthorization
from raven.fathom.base import Package
from raven.fathom.base import DeploymentMessage
from raven.fathom.base import User
from raven.fathom.base import Project
from raven.fathom.base.context import APPLICATION_NAME
from raven.fathom.client.logging import Logger
from raven.fathom.client.signup import UserSignupRequest, ResultStatus
from raven.fathom.client.signup import SignupConnectionException
from raven.fathom.client.exceptions import FathomClientException

if TYPE_CHECKING:
    from raven.fathom.client.locator import ServerLocator


LOG = Logger.get()

T = TypeVar("T")

S = TypeVar("S", bound=Sized)


class ServerConnectionException(FathomClientException):
    """A failed connection or communication with the server.

    This is the main exception type for the higher-level `Server` API.
    It is raised for connection and networking errors, as well as any
    server-side refusal or processing error that is not due to validation
    failures of the underlying request input.
    """


@dataclass
class Result:
    """The `Server` API result type.

    Attributes:
        ok (bool): Indicates whether the request has succeeded. If `False`,
            then `errors` may contain errors messages indicative
            of the problem.
        messages (list): Informational list of messages from the server.
        warnings (list): Warning messages from the server.
        errors (list): Error messages from the server. If `ok` is `True`,
            then this list is empty.
    """

    ok: bool = field(
        init=False,
        default=False,
    )

    messages: list[str] = field(
        init=False,
        default_factory=list,
    )

    warnings: list[str] = field(
        init=False,
        default_factory=list,
    )

    errors: list[str] = field(
        init=False,
        default_factory=list,
    )


@dataclass
class DataResult(Result, Generic[T]):
    """The `Server` API result type for server requests that return data.

    Attributes:
        data (T): The returned data from the server. If `ok` is `False`,
            then this attribute must not be used as it may be `None`.
    """

    data: T


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

    Attributes:
        name (str): The name of the server instance. Is taken from the
            specified server locator object.
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

    @property
    def name(self) -> Optional[str]:
        """The name of the server, as a `str`.

        May be `None`.
        """
        return self._location.server_name

    def request_server_info(self) -> DataResult[ServerInfo]:
        """Requests state information from the server.

        Returns:
            DataResult[ServerInfo]: The information provided by the server.

        Raises:
            ServerConnectionException: If a connection to the server cannot
                be established or the request encounters an unexpected error.
        """
        request = ClientRequest(Interaction.QUERY_SERVER_INFO)
        request.authentication = self._client_authentication

        LOG.v("Requesting general information from server")
        response = self._send(request)
        result = self._prepare_result(response)
        if result.ok:
            server_info = self._create_server_info_obj(
                self._get_data_object_from(response.server_info)
            )
            return self._combine(result, server_info)

        return self._empty(result)

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
                be established or the request encounters an unexpected error.
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
                be established or the request encounters an unexpected error.
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

    def create_user(self, user: User) -> DataResult[User]:
        """Creates a regular application user on the server.

        Args:
            user (User): The User object to create on the server.

        Returns:
            DataResult[User]: The created user as returned by the server.

        Raises:
            ServerConnectionException: If a connection to the server cannot
                be established or the request encounters an unexpected error.
        """
        request = ClientRequest(Interaction.CREATE_USER)
        request.authentication = self._client_authentication
        request.user = user

        LOG.v("Requesting remote user creation")
        response = self._send(request)
        result = self._prepare_result(response)
        if result.ok:
            users = self._get_data_object_from(response.users)
            return self._combine(result, users[0])

        return self._empty(result)

    def sign_up_user(self, user: User) -> Result:
        """Initializes an onboarding application user on the server.

        Args:
            user (User): The base User object for which to complete the
                setup procedure.

        Returns:
            Result: The result of the signup operation.

        Raises:
            ServerConnectionException: If a connection to the server cannot
                be established or the request encounters an unexpected error.
        """
        if self._client_authentication is None:
            raise ServerConnectionException(
                "Authentication must be provided "
                "when signing up a new user"
            )

        LOG.v("Requesting remote user setup")
        try:
            return self._send_user_signup_request(user)
        except SignupConnectionException as ex:
            raise ServerConnectionException(
                "Could not establish a connection to the server"
            ) from ex

    def list_users(self) -> DataResult[list[User]]:
        """Lists application users from the server.

        Returns:
            DataResult[list]: A `list` of `User` objects managed by
                the Fathom server, encapsulated in a `DataResult` object.

        Raises:
            ServerConnectionException: If a connection to the server cannot
                be established or the request encounters an unexpected error.
        """
        request = ClientRequest(Interaction.LIST_USERS)
        request.authentication = self._client_authentication

        LOG.v("Requesting remote user list")
        response = self._send(request)
        result = self._prepare_result(response)
        if result.ok:
            users = self._get_data_list_from(response.users)
            return self._combine(result, users)

        return self._empty(result)

    def delete_user(self, identifier: str) -> Result:
        """Deletes an application user on the server.

        Args:
            identifier (str): The identifier of the user to delete.

        Returns:
            Result: The result of the deletion operation.

        Raises:
            ServerConnectionException: If a connection to the server cannot
                be established or the request encounters an unexpected error.
        """
        request = ClientRequest(Interaction.DELETE_USER)
        request.authentication = self._client_authentication
        request.user = User(identifier=identifier)

        LOG.v("Requesting remote user deletion")
        response = self._send(request)
        return self._prepare_result(response)

    def assign_user_to_project(
        self,
        user_identifier: str,
        project_identifier: str
    ) -> Result:
        """Assigns an application user to a project on the server.

        Args:
            user_identifier (str): The identifier of the user to assign.
            project_identifier (str): The identifier of the project to assign
                the user to.

        Returns:
            Result: The result of the assignment operation.

        Raises:
            ServerConnectionException: If a connection to the server cannot
                be established or the request encounters an unexpected error.
        """
        request = ClientRequest(Interaction.ASSIGN_USER)
        request.authentication = self._client_authentication
        request.user = User(identifier=user_identifier)
        request.project = Project(identifier=project_identifier)

        LOG.v("Requesting remote user-project assignment")
        response = self._send(request)
        return self._prepare_result(response)

    def unassign_user_from_project(
        self,
        user_identifier: str,
        project_identifier: str
    ) -> Result:
        """Unassigns an application user from a project on the server.

        Args:
            user_identifier (str): The identifier of the user to unassign.
            project_identifier (str): The identifier of the project to remove
                the user from.

        Returns:
            Result: The result of the unassignment operation.

        Raises:
            ServerConnectionException: If a connection to the server cannot
                be established or the request encounters an unexpected error.
        """
        request = ClientRequest(Interaction.UNASSIGN_USER)
        request.authentication = self._client_authentication
        request.user = User(identifier=user_identifier)
        request.project = Project(identifier=project_identifier)

        LOG.v("Requesting remote user-project unassignment")
        response = self._send(request)
        return self._prepare_result(response)

    def create_project(self, project: Project) -> DataResult[Project]:
        """Creates a project on the server.

        Args:
            project (Project): The project to create on the server.

        Returns:
            DataResult[Project]: The created project as returned by the server.

        Raises:
            ServerConnectionException: If a connection to the server cannot
                be established or the request encounters an unexpected error.
        """
        request = ClientRequest(Interaction.CREATE_PROJECT)
        request.authentication = self._client_authentication
        request.project = project

        LOG.v("Requesting remote project creation")
        response = self._send(request)
        result = self._prepare_result(response)
        if result.ok:
            projects = self._get_data_object_from(response.projects)
            return self._combine(result, projects[0])

        return self._empty(result)

    def list_projects(self) -> DataResult[list[Project]]:
        """Lists projects from the server.

        Returns:
            DataResult[list]: A `list` of `Project` objects managed by the
                Fathom server, encapsulated in a `DataResult` object.

        Raises:
            ServerConnectionException: If a connection to the server cannot
                be established or the request encounters an unexpected error.
        """
        request = ClientRequest(Interaction.LIST_PROJECTS)
        request.authentication = self._client_authentication

        LOG.v("Requesting remote project list")
        response = self._send(request)
        result = self._prepare_result(response)
        if result.ok:
            projects = self._get_data_list_from(response.projects)
            return self._combine(result, projects)

        return self._empty(result)

    def list_project_users(self, identifier: str) -> DataResult[list[User]]:
        """Lists all users assigned to a project from the server.

        Args:
            identifier (str): The identifier of the project to query.

        Returns:
            DataResult[list]: A `list` of `User` objects assigned to the
                project, encapsulated in a `DataResult` object.

        Raises:
            ServerConnectionException: If a connection to the server cannot
                be established or the request encounters an unexpected error.
        """
        request = ClientRequest(Interaction.LIST_PROJECT_USERS)
        request.authentication = self._client_authentication
        request.project = Project(identifier=identifier)

        LOG.v("Requesting remote project-user list")
        response = self._send(request)
        result = self._prepare_result(response)
        if result.ok:
            users = self._get_data_list_from(response.users)
            return self._combine(result, users)

        return self._empty(result)

    def delete_project(self, identifier: str) -> Result:
        """Deletes a project on the server.

        Args:
            identifier (str): The identifier of the project to delete.

        Returns:
            Result: The result of the deletion operation.

        Raises:
            ServerConnectionException: If a connection to the server cannot
                be established or the request encounters an unexpected error.
        """
        request = ClientRequest(Interaction.DELETE_PROJECT)
        request.authentication = self._client_authentication
        request.project = Project(identifier=identifier)

        LOG.v("Requesting remote project deletion")
        response = self._send(request)
        return self._prepare_result(response)

    def _create_server_info_obj(self, server_info_map):
        server_info = ServerInfo()
        server_info.server_agent = server_info_map.get("server_agent")
        server_info.app_version = server_info_map.get("app_version", "")
        return server_info

    def _prepare_result(self, response: ServerResponse) -> Result:
        result = Result()
        if response.has_warnings():
            result.warnings.extend(
                map(lambda warning: warning.text, response.warnings)
            )

        if response.has_errors():
            self._raise_on_unrecoverable_error(response)
            result.ok = False
            result.errors.extend(
                map(lambda error: error.text, response.errors)
            )
        else:
            result.ok = True
            if response.has_code(ResponseCode.SUCCESSFUL_COMPLETION):
                result.messages.extend(
                    map(lambda info: info.text, response.infos)
                )
            else:
                result.warnings.append(
                    "No errors were detected but the server response "
                    "did not explicitly indicate successful completion."
                )

        return result

    def _raise_on_unrecoverable_error(self, response):
        unrecoverable_codes = self._unrecoverable_errors()
        for error in response.errors:
            if error.code in unrecoverable_codes:
                raise ServerConnectionException(error.text)

    def _unrecoverable_errors(self):
        return (
            ResponseCode.CLIENT_VERSION_NOT_SUPPORTED,
            ResponseCode.UNSUPPORTED_ACTION,
        )

    def _empty(self, result: Result) -> DataResult:
        return self._combine(result, data=None)

    def _combine(self, result: Result, data: T) -> DataResult[T]:
        data_result = DataResult[T](data=data)
        assert issubclass(DataResult, Result)
        for field_def in fields(result):
            setattr(
                data_result,
                field_def.name,
                getattr(result, field_def.name)
            )

        return data_result

    def _get_data_object_from(self, response_data: Optional[S]) -> S:
        if response_data is None or len(response_data) != 1:
            raise ServerConnectionException(
                "Server response does not contain expected payload data. "
                "Expected list of size 1"
            )

        return response_data

    def _get_data_list_from(self, response_data: Optional[T]) -> T:
        if response_data is None:
            raise ServerConnectionException(
                "Server response does not contain expected payload data. "
                "Expected list is missing"
            )

        return response_data

    def _send_user_signup_request(self, user):
        assert self._client_authentication is not None
        request = UserSignupRequest(
            self._location,
            self._client_authentication,
            user
        )
        response = request.send()
        result = Result()
        if response.status == ResultStatus.OK:
            result.ok = True
            result.messages.append(response.message)
        else:
            result.ok = False
            result.errors.append(response.message)

        return result

    def _send(self, request):
        try:
            return ServerInteraction.instance(self._location).process(request)
        except TransmissionException as ex:
            LOG.v("Failed to transmit request to %s server:", APPLICATION_NAME)
            LOG.v("%s", ex)
            raise ServerConnectionException(
                "Could not establish a connection to the server"
            ) from ex
        except ProcessingException as ex:
            LOG.v(
                "The request was transmitted to the %s server "
                "but it encountered an unexpected error:",
                APPLICATION_NAME,
            )
            LOG.v("%s", ex)
            raise ServerConnectionException(
                "The server failed to process the request"
            ) from ex
        except InteractionException as ex:
            LOG.v("Failed to interact with %s server:", APPLICATION_NAME)
            LOG.v("%s", ex)
            raise ServerConnectionException(
                "An unknown error has occurred while communicating "
                "with the server"
            ) from ex
