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
"""Management of tracked projects."""

from raven.fathom.base import TypeCheck
from raven.fathom.base import Project
from raven.fathom.base import User
from raven.fathom.server.dao import DataAccess
from raven.fathom.server.dao import FailedReadQueryException
from raven.fathom.server.dao import FailedCreateQueryException
from raven.fathom.server.dao import FailedDeleteQueryException
from raven.fathom.server.models import AuthDeployment
from raven.fathom.server.models import ProjectVersion
from raven.fathom.server.models import StagingAllocation
from raven.fathom.server.models import UserProjectRel
from raven.fathom.server.models import Project as ProjectModel
from raven.fathom.server.core.exceptions import FathomServerException


class ProjectManagementException(FathomServerException):
    """Base class for project-management domain failures."""


class InvalidProjectRequestException(ProjectManagementException):
    """A precondition for a requested operation was not met or some input
    given to a requested operation was invalid.
    """


class ProjectNotFoundException(InvalidProjectRequestException):
    """An operation was requested for a project that does not
    actually exist.
    """


class ProjectAlreadyExistsException(InvalidProjectRequestException):
    """An attempt was made to create a project that already exists."""


class ProjectInternalException(ProjectManagementException):
    """Infrastructure has failed unexpectedly.

    Signals a lower-level internal system error that is not a caller mistake.
    """


class ProjectManager:
    """Provides methods to manage deployable projects."""

    def __init__(self):
        """Initializes a new `ProjectManager` instance."""
        self._ds = DataAccess.instance()

    def create_project(self, project: Project):
        """Creates a new project on the server.

        Args:
            project (Project): The project to create.

        Raises:
            ProjectManagementException: If the given project cannot be created.
        """
        TypeCheck.require_arg(project.identifier, str)
        if not project.identifier:
            raise InvalidProjectRequestException(
                "Cannot create a new project. "
                "Project identifier must not be empty"
            )

        project_record = self._ds.projects().find_by_identifier(
            project.identifier
        )
        if project_record is not None:
            raise ProjectAlreadyExistsException(
                f"Cannot create project '{project.identifier}' "
                "because the project already exists"
            )

        if not project.name:
            project.name = project.identifier

        if not project.description:
            project.description = ""

        project_record = ProjectModel(
            identifier=project.identifier,
            name=project.name,
            description=project.description,
            latest_version="",
        )
        try:
            self._ds.projects().create(project_record)
        except FailedCreateQueryException as ex:
            raise ProjectInternalException(
                f"Failed to create project '{project.identifier}'. "
                "An internal error has occurred."
            ) from ex

    def list_projects(self) -> list[Project]:
        """Lists all projects registered in the server backend.

        Returns:
            list: A `list` of `Project` objects managed by the Fathom server.

        Raises:
            ProjectManagementException: If projects cannot be listed.
        """
        try:
            return [
                Project(
                    identifier=str(project.identifier),
                    name=str(project.name),
                    description=str(project.description),
                ) for project in self._ds.projects().read_all()
            ]
        except FailedReadQueryException as ex:
            raise ProjectInternalException(
                "Failed to obtain list of registered projects. "
                "An internal error has occurred."
            ) from ex

    def list_project_users(self, project: Project) -> list[User]:
        """Lists all users assigned to a registered project.

        Args:
            project (Project): The project whose assigned users to list.

        Returns:
            list: A `list` of `User` objects assigned to the project.

        Raises:
            ProjectManagementException: If project users cannot be listed.
        """
        TypeCheck.require_arg(project.identifier, str)
        if not project.identifier:
            raise InvalidProjectRequestException(
                "Cannot list project users. "
                "Project identifier must not be empty"
            )

        project_record = self._ds.projects().find_by_identifier(
            project.identifier
        )
        if project_record is None:
            raise ProjectNotFoundException(
                f"Cannot list users for project '{project.identifier}'. "
                "The project does not exist"
            )

        try:
            projects = self._ds.projects()
            return [
                User(
                    identifier=str(user.identifier),
                    name=str(user.name),
                )
                for user in projects.find_all_users_assigned_to_project(
                    project_record
                )
            ]
        except FailedReadQueryException as ex:
            raise ProjectInternalException(
                "Failed to obtain list of users assigned "
                f"to project '{project.identifier}'. "
                "An internal error has occurred."
            ) from ex

    def delete_project(self, project: Project):
        """Deletes a project from the server backend.

        Args:
            project (Project): The project to delete.

        Raises:
            ProjectManagementException: If the project could not be deleted.
        """
        TypeCheck.require_arg(project.identifier, str)
        if not project.identifier:
            raise InvalidProjectRequestException(
                "Cannot delete project. "
                "Project identifier must not be empty"
            )

        project_record = self._ds.projects().find_by_identifier(
            project.identifier
        )
        if project_record is None:
            raise ProjectNotFoundException(
                f"Cannot delete project '{project.identifier}'. "
                "The project does not exist"
            )

        try:
            # pylint: disable=not-an-iterable
            auth_records = AuthDeployment.select().where(
                AuthDeployment.project == project_record
            )
            for auth_record in auth_records:
                self._ds.data(AuthDeployment).delete(auth_record)

            relations = UserProjectRel.select().where(
                UserProjectRel.project == project_record
            )
            for relation in relations:
                self._ds.data(UserProjectRel).delete(relation)

            versions = ProjectVersion.select().where(
                ProjectVersion.project == project_record
            )
            for version in versions:
                allocations = StagingAllocation.select().where(
                    StagingAllocation.project_version == version
                )
                for allocation in allocations:
                    self._ds.data(StagingAllocation).delete(allocation)

                self._ds.data(ProjectVersion).delete(version)

            self._ds.projects().delete(project_record)
        except FailedDeleteQueryException as ex:
            raise ProjectInternalException(
                f"Failed to delete project '{project.identifier}'. "
                "An internal error has occurred."
            ) from ex
