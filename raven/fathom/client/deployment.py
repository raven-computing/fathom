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
"""Client management API for Fathom deployments."""

from typing import Optional

from raven.fathom.base import ClientAuthentication
from raven.fathom.base import ClientDeploymentIntent
from raven.fathom.base import PackageOperationException
from raven.fathom.base import TypeCheck
from raven.fathom.client.logging import Logger
from raven.fathom.client.project import Project
from raven.fathom.client.documentation import DocumentationResource
from raven.fathom.client.package import DocumentationPackage
from raven.fathom.client.locator import ServerLocator
from raven.fathom.client.connection import Server
from raven.fathom.client.exceptions import FathomClientException


LOG = Logger.get()


class DeploymentException(FathomClientException):
    """A failed Fathom deployment."""


class DeploymentResult:
    """The result of a Fathom deployment.

    A `DeploymentResult` object is returned by a `FathomDeployment` instance
    as a result of a `FathomDeployment.deploy()` instruction.

    Attributes:
        info_message (str): An info message from the server. May be `None`.
    """

    def __init__(self):
        """Initializes a new `DeploymentResult` instance."""
        self._is_successful = False
        self._info_message = None
        self._errors = None
        self._warnings = None

    @property
    def info_message(self) -> Optional[str]:
        """An info message from the server. May be `None`."""
        return self._info_message

    @info_message.setter
    def info_message(self, value):
        if value is not None:
            TypeCheck.require_prop(value, str, "info_message")

        self._info_message = value

    def is_successful(self) -> bool:
        """Indicates whether the underlying deployment was successful.

        Returns:
            bool: `True` if the deployment was successfull.
                `False` if the deployment has failed for any reason.
        """
        return self._is_successful

    def set_successful(self, value: bool):
        """Sets this result as either successfull or unsuccessfull."""
        TypeCheck.require_arg(value, bool)
        self._is_successful = value


class FathomDeployment:
    """A Fathom deployment.

    This is the primary mechanism by which Fathom clients can execute a
    documentation resource deployment.
    """

    def __init__(self, location: ServerLocator):
        """Initializes a new `FathomDeployment` instance.

        The created instance is empty, i.e it has no deployment resource set.
        """
        TypeCheck.require_arg(location, ServerLocator)
        self._location = location
        self._project = None
        self._resource = None
        self._client_authentication = None

    @property
    def location(self) -> ServerLocator:
        """The location of the Fathom server to which this deployment
        will be sent.

        Returns:
            ServerLocator: The server locator for this deployment.
        """
        return self._location

    def use_authentication(
        self,
        authentication: Optional[ClientAuthentication]
    ):
        """Sets the specified authentication for the deployment.

        Args:
            authentication (ClientAuthentication): The client authentication
                to use. May be `None` to not use any authentication.
        """
        if authentication is not None:
            TypeCheck.require_arg(authentication, ClientAuthentication)

        self._client_authentication = authentication

    def has_project(self) -> bool:
        """Indicates whether this deployment has a project set.


        Returns:
            bool: `True` if this deployment has a project set,
                `False` if no project is currently set.
        """
        return self._project is not None

    def get_project(self) -> Optional[Project]:
        """Gets the project of this deployment.

        Returns:
            Project: The project of this deployment.
                May be `None` if no project is currently set.
        """
        return self._project

    def set_project(self, project: Optional[Project]):
        """Sets the project for this deployment.

        Args:
            project (Project): The project to set.
                May be `None` to not have any project set.
        """
        if project is not None:
            TypeCheck.require_arg(project, Project)

        self._project = project

    def has_resource(self) -> bool:
        """Indicates whether this deployment has a resource set.

        Returns:
            bool: `True` if this deployment has a resource set, `False` if
                no resource is currently set.
        """
        return self._resource is not None

    def add_resource(self, resource: DocumentationResource):
        """Adds the specified documentation resource to this deployment.

        Args:
            resource (DocumentationResource): The documentation resource to
                add to this Fathom deployment.

        Raises:
            DeploymentException: If a resource is already set.
        """
        if self.has_resource():
            raise DeploymentException("Deployment resource is already set")

        TypeCheck.require_arg(resource, DocumentationResource)
        self._resource = resource

    def clear_resource(self):
        """Clears any previously set deployment resource."""
        self._resource = None

    def deploy(self) -> DeploymentResult:
        """Executes a Fathom documentation deployment.

        Returns:
            DeploymentResult: The result of the deployment attempt.

        Raises:
            DeploymentException: If any precondition for deployment is not met.
            ServerConnectionException: If the client could not communicate with
                the Fathom server.
        """
        self._check_deployment_preconditions()

        server = Server(self._location, self._client_authentication)
        intent = ClientDeploymentIntent()
        intent.project = self.get_project()

        deployment_authorization = server.request_deployment(intent)
        if not deployment_authorization.is_granted():
            return self._unauthorized(deployment_authorization)

        package = self._prepare_package()
        response = server.transact_deployment(
            deployment_authorization,
            package
        )

        result = DeploymentResult()
        result.set_successful(response.is_successful)
        result.info_message = response.message
        return result

    def _check_deployment_preconditions(self):
        LOG.d("Checking deployment preconditions")
        if not self.has_resource():
            raise DeploymentException(
                "No documentation resource set for deployment"
            )

        if not self.has_project():
            raise DeploymentException(
                "No project set for deployment"
            )

    def _prepare_package(self):
        LOG.d("Preparing package for deployment")
        assert self._resource is not None
        package = DocumentationPackage(self._resource).adapt()
        try:
            package.pack()
        except PackageOperationException as ex:
            raise DeploymentException("Failed to package resources") from ex
        finally:
            try:
                package.release()
            except PackageOperationException:
                LOG.w("Package resources were not properly released")

        return package

    def _unauthorized(self, deployment_authorization):
        result = DeploymentResult()
        result.set_successful(False)
        result.info_message = (
            "Deployment authorization not granted: "
            f"{deployment_authorization.status} "
            f"{deployment_authorization.status.message()}"
        )
        return result
