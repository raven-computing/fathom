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
"""Deployment of resources.

Provides the `DeploymentManager` class which implements the deployment of
resources in form of a `Package` to the Fathom server.
"""

from dataclasses import dataclass

from raven.fathom.base import Configuration, ApplicationContext
from raven.fathom.base import File, FileIOException
from raven.fathom.base import FileCreationException, FilePermissionException
from raven.fathom.base import ClientDeploymentIntent
from raven.fathom.base import Project, Package
from raven.fathom.server.logging import Logger
from raven.fathom.server.config import ServerConfiguration
from raven.fathom.server.exceptions import FathomServerException
from raven.fathom.server.staging import StagingArea, StagingAreaException


LOG = Logger.get()


class ServerDeploymentException(FathomServerException):
    """Base class for all failed deployment operations on the Fathom server."""


class InaccessibleDeploymentSiteException(ServerDeploymentException):
    """Signals that the deployment site cannot be accessed or created."""


class DeploymentExecutionException(ServerDeploymentException):
    """Signals a failed deployment execution."""


class DeploymentSite:
    """Represents the resource deployment site.

    This is a location in the filesystem where the resources of deployed
    projects are stored, i.e. the final destination of the resources.
    """

    def __init__(self, config: Configuration):
        """Initializes a new `DeploymentSite` instance.

        Args:
            config (Configuration): The configuration of the Fathom server.
        
        Raises:
            MissingRequiredConfigurationException: If the deployment site
                directory is not configured in the server configuration.
        """
        self._config = config
        self._site_dir = self._determine_root_directory()

    @property
    def directory(self) -> File:
        """The root directory of the deployment site within the filesystem.

        Returns:
            File: A `File` referring to the deployment site root directory.
        """
        return File(self._site_dir)

    def create(self):
        """Creates the deployment site directory if it does not exist.

        Raises:
            InaccessibleDeploymentSiteException: If the deployment site cannot
                be created or accessed.
        """
        directory = self._site_dir
        if directory.exists():
            if not directory.is_directory():
                raise InaccessibleDeploymentSiteException(
                    "Deployment area cannot be created because a file at "
                    "that path already exists but "
                    f"is not a directory: '{directory}'"
                )

            if not directory.is_writable():
                raise InaccessibleDeploymentSiteException(
                    "Deployment area cannot be created "
                    "because a directory at that path already exists "
                    f"but is not writable: '{directory}'"
                )

        else:
            try:
                directory.create_directory_tree()
            except FilePermissionException as ex:
                raise InaccessibleDeploymentSiteException(
                    "Failed to create deployment area directory tree. "
                    "The application is not allowed to create directories "
                    "at the deployment site. Permission must be granted "
                    "to the application at the filesystem-level to create "
                    f"directories at the deployment site '{directory}'"
                ) from ex
            except FileCreationException as ex:
                raise InaccessibleDeploymentSiteException(
                    "An I/O error occurred while creating the deployment "
                    f"area directory tree '{directory}'"
                ) from ex

    def has_file_system_access(self) -> bool:
        """Checks whether the application can access the deployment site
        in the filesystem.
        """
        try:
            return self._check_site_dir_access()
        except FileIOException as ex:
            LOG.e(
                "File I/O error while checking deployment site access: %s", ex
            )
            return False

    def contains(self, project: Project) -> bool:
        """Checks whether the deployment site contains resources for the given
        project.

        Args:
            project (Project): The project to check for. If a project version
                is set, the check will be performed for that specific version.
                If no project version is set, the check will be performed for
                the project in general.

        Returns:
            bool: `True` if the deployment site contains resources for the
                given project, `False` otherwise.
        """
        return self._get_project_site_path(project).exists()

    def get_target_directory(self, project: Project) -> File:
        """Gets the target directory for the given project
        in the deployment site.

        Args:
            project (Project): The project for which to get the target
                directory. If a project version is set, the target directory
                will be returned for that specific version. If no project
                version is set, the target directory will be returned for the
                project in general.

        Returns:
            File: A `File` referring to the target directory for the given
                project in the deployment site.
        """
        return self._get_project_site_path(project)

    def _get_project_site_path(self, project):
        project_root = File(project.identifier)
        if project.version is not None:
            project_version = File(project.version.identifier)
            return self._site_dir / project_root / project_version

        return self._site_dir / project_root

    def _check_site_dir_access(self):
        if not self._site_dir.is_directory():
            return False

        site_access = self._site_dir.access()
        if not site_access.can_read or not site_access.can_write:
            return False

        return True

    def _determine_root_directory(self):
        site_directory = self._config.get_required_value(
            ServerConfiguration.SERVER.DEPLOYMENT_SITE_DIRECTORY
        )

        if not site_directory.path.is_absolute():
            root_base = self._get_default_root_base_directory()
            return root_base / site_directory

        return site_directory

    def _get_default_root_base_directory(self):
        return ApplicationContext.instance().get_working_directory()


@dataclass
class DeploymentResult:
    """The result of an executed deployment.

    Attributes:
        successful (bool): Whether the deployment was successful.
        user_message (str): A message to be displayed to the user.
    """

    successful: bool

    user_message: str


class DeploymentExecutor:
    """An executor for a deployment.
    
    Moves resources from the staging area to the deployment site
    for a given project.
    """

    def __init__(self, sa: StagingArea, ds: DeploymentSite):
        self._staging_area = sa
        self._deployment_site = ds

    def deploy(self, project: Project):
        """Executes a deployment for the given project.

        Args:
            project (Project): The project for which to deploy the resources
                of this executor. Must have a project version set.

        Raises:
            DeploymentExecutionException: If the resources cannot be deployed.
        """
        if not project.version:
            raise DeploymentExecutionException(
                "Project version not set"
                f" for project '{project.name}' ({project.identifier})"
            )

        resource = self._staging_area.get_allocation_directory(project)
        target_directory = self._deployment_site.get_target_directory(project)
        self._ensure_target_directory_ready(target_directory)
        self._deploy_target(resource, target_directory)
        self._clean_up_staging(project)

    def _deploy_target(self, resource_directory: File, target_directory: File):
        try:
            resource_directory.move(target_directory)
        except FileIOException as ex:
            raise DeploymentExecutionException(
                "Failed to move data from staging area to target directory"
            ) from ex

    def _clean_up_staging(self, project: Project):
        try:
            self._staging_area.remove(project)
        except StagingAreaException as ex:
            raise DeploymentExecutionException(
                "Target was deployed but failed to clean up staging area "
                f"for project {project}"
            ) from ex

    def _ensure_target_directory_ready(self, target_directory: File):
        parent = target_directory.get_parent_directory()
        try:
            parent.create_directory_tree()
        except FileIOException as ex:
            raise DeploymentExecutionException(
                "Failed to create target parent directory "
                f"for deployment ({parent})"
            ) from ex


class DeploymentManager:
    """Manages Fathom server deployments."""

    def __init__(self, config: Configuration):
        """Initializes a new `DeploymentManager` instance.

        Args:
            config (Configuration): The configuration of the Fathom server.
        """
        self._config = config

    def deploy(
        self,
        intent: ClientDeploymentIntent,
        package: Package
    ) -> DeploymentResult:
        """Performs a deployment for the given package.

        The given intent is considered to be what the underlying client is
        allowed to do. Proper authorization must have already been performed.

        Args:
            intent (ClientDeploymentIntent): The requested deployment.
                Must already be validated and authorized.
            package (Package): The data package to deploy.

        Returns:
            DeploymentResult: The result of the requested deployment operation.

        Raises:
            MissingRequiredConfigurationException: If the configuration of
                the Fathom server is missing required values.
            StagingAreaException: If the staging area cannot be accessed
                or used.
            DeploymentExecutionException: If an unexpected error occurs.
        """
        project = intent.project
        if project is None:
            return DeploymentResult(
                successful=False,
                user_message="Cannot deploy package without project"
            )

        deployment_site = DeploymentSite(self._config)
        if deployment_site.contains(project) and not intent.overwrite_existing:
            return DeploymentResult(
                successful=False,
                user_message=(
                    f"Cannot deploy project {project} as it is already "
                    "deployed and the 'overwrite existing' setting "
                    "was disabled or not authorized."
                )
            )

        staging_area = StagingArea(self._config)
        staging_area.put(project, package)
        DeploymentExecutor(staging_area, deployment_site).deploy(project)
        return DeploymentResult(
            successful=True,
            user_message=f"Successfully deployed package for {project}",
        )
