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
"""Data access object declaration for project-related data."""

from abc import abstractmethod
from typing import Optional, Union

from raven.fathom.server.dao.base import DataAccessObject
from raven.fathom.server.models import Project, ProjectVersion
from raven.fathom.server.models import User, StagingAllocation


class ProjectDAO(DataAccessObject):
    """A data access object for project-related data."""

    @abstractmethod
    def find_by_identifier(self, identifier: str) -> Optional[Project]:
        """Gets the project record with the specified identifier.

        Args:
            identifier (str): The unique identifier of the project to get.

        Returns:
            Project: The `Project` object with the specified identifier,
                or `None` if no such project can be found.
        """

    @abstractmethod
    def find_version_by_identifier(
        self,
        project: Union[Project, str],
        identifier: str
    ) -> Optional[ProjectVersion]:
        """Gets the project version record with the specified identifier.

        Args:
            project (Project | str): The `Project` record or its ID for which
                to find the specific project version record for. May also be
                specified as a `str` which will look up the project by its
                unique string identifier.
            identifier (str): The version identifier of the project to get.

        Returns:
            ProjectVersion: The `ProjectVersion` object with the specified
                identifier, or `None` if no such project version can be found.
        """

    @abstractmethod
    def find_all_assigned_to_user(self, user: User) -> list[Project]:
        """Finds all projects which are assigned to the given user.

        Args:
            user (User): The user to find all assigned projects for.

        Returns:
            list: All `Project` records assigned to the specified user.
        """

    @abstractmethod
    def assign_user_to_project(self, user: User, project: Project):
        """Assigns the given user to the specified project.

        Creates the corresponding relation within the data source.

        Args:
            user (User): The user to assign to the project.
            project (Project): The project to which the user
                should be assigned to.
        """

    @abstractmethod
    def find_staging_allocations(
        self,
        project: Project
    ) -> list[StagingAllocation]:
        """Finds all staging allocations committed to the given project.

        Args:
            project (Project): The project to find staging allocations for.

        Returns:
            list: All `StagingAllocation` records for the specified project.
        """

    @abstractmethod
    def find_staging_allocation(
        self,
        project: ProjectVersion
    ) -> Optional[StagingAllocation]:
        """Finds the one staging allocation committed to the project
        in the given version.

        Args:
            project (ProjectVersion): The concrete version of the project
                to find a committed staging allocation for.

        Returns:
            StagingAllocation: The `StagingAllocation` record for the
                specified project version. May be `None` if no staging
                allocation could be found.
        """

    @abstractmethod
    def delete_staging_allocation(self, project: ProjectVersion):
        """Deletes the staging allocation for the given version of the project.

        Args:
            project (ProjectVersion): The project version for which to delete a
                previously committed staging allocation.
        """
