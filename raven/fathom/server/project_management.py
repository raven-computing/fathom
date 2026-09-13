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
from raven.fathom.server.dao import DataAccess
from raven.fathom.server.dao import FailedCreateQueryException
from raven.fathom.server.dao import FailedDeleteQueryException
from raven.fathom.server.models import AuthDeployment
from raven.fathom.server.models import ProjectVersion
from raven.fathom.server.models import StagingAllocation
from raven.fathom.server.models import UserProjectRel
from raven.fathom.server.models import Project as ProjectModel


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
            ValueError: If the given project cannot be created.
        """
        TypeCheck.require_arg(project.identifier, str)
        if not project.identifier:
            raise ValueError("Project identifier must not be empty")

        project_record = self._ds.projects().find_by_identifier(
            project.identifier
        )
        if project_record is not None:
            raise ValueError(f"Project '{project.identifier}' already exists")

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
            raise ValueError(
                f"Failed to create project '{project.identifier}'"
            ) from ex

    def list_projects(self) -> list[Project]:
        """Lists all projects registered in the server backend.

        Returns:
            list: A `list` of `Project` objects managed by the Fathom server.
        """
        return [
            Project(
                identifier=str(project.identifier),
                name=str(project.name),
                description=str(project.description),
            ) for project in self._ds.projects().read_all()
        ]

    def delete_project(self, project: Project):
        """Deletes a project from the server backend.

        Args:
            project (Project): The project to delete.

        Raises:
            ValueError: If the given project is invalid or could not
                be deleted.
        """
        TypeCheck.require_arg(project.identifier, str)
        if not project.identifier:
            raise ValueError("Project identifier must not be empty")

        project_record = self._ds.projects().find_by_identifier(
            project.identifier
        )
        if project_record is None:
            raise ValueError(f"Project '{project.identifier}' does not exist")

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
            raise ValueError(
                f"Failed to delete project '{project.identifier}'"
            ) from ex
