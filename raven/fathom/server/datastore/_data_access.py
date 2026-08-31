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
"""Implementation of the data access API for relational database persistence
using query builders from the peewee ORM.
"""

from typing import cast

from raven.fathom.server.dao import DataAccess, DataAccessObject
from raven.fathom.server.dao import IncoherentDatastoreStateException
from raven.fathom.server.dao import UserDAO, ProjectDAO
from raven.fathom.server.models import User, Project, ProjectVersion
from raven.fathom.server.models import UserProjectRel
from raven.fathom.server.models import UserPermission
from raven.fathom.server.models import StagingAllocation
from raven.fathom.server.models import AuthDeployment
from raven.fathom.server.datastore.orm.query import CreateQuery, ReadQuery
from raven.fathom.server.datastore.orm.query import UpdateQuery, DeleteQuery


class DataAccessObjectRDBMS(DataAccessObject):
    """Implementation of the `DataAccessObject` ABC for RDBMS persistence."""

    def create(self, record):
        CreateQuery(record).execute()

    def update(self, record):
        UpdateQuery(record).execute()

    def delete(self, record):
        DeleteQuery(record).execute()


class _UserDAOImpl(DataAccessObjectRDBMS, UserDAO):

    def find_by_identifier(self, identifier):
        return ReadQuery[User](
            User.select().where(User.identifier == identifier)
        ).find_one()

    def find_permission(self, user):
        permission = ReadQuery[UserPermission](
            UserPermission.select().where(UserPermission.user == user)
        ).find_one()

        if permission is None:
            raise IncoherentDatastoreStateException(
                f"Missing {UserPermission} record "
                f"associated with {User} record with ID {user}"
            )

        return permission

    def find_deployment_authorization_by_token(self, token: str):
        return ReadQuery[AuthDeployment](
            AuthDeployment.select().where(AuthDeployment.token == token)
        ).find_one()


class _ProjectDAOImpl(DataAccessObjectRDBMS, ProjectDAO):

    def find_by_identifier(self, identifier):
        return ReadQuery[Project](
            Project.select().where(Project.identifier == identifier)
        ).find_one()

    def find_version_by_identifier(self, project, identifier):
        if isinstance(project, str):
            project_selection = Project.identifier == project
        else:
            project_selection = project

        return ReadQuery[ProjectVersion](
            ProjectVersion.select().where(
                project_selection
                and ProjectVersion.version_identifier == identifier
            )
        ).find_one()

    def find_all_assigned_to_user(self, user):
        user_id = user.id # type: ignore
        return [
            cast(Project, user_project_rel.project)
            for user_project_rel in ReadQuery[UserProjectRel](
                UserProjectRel.select().where(UserProjectRel.user == user_id)
            ).execute()
        ]

    def assign_user_to_project(self, user, project):
        UserProjectRel.create(
            user=user,
            project=project,
        )

    def find_staging_allocations(self, project):
        if isinstance(project, str):
            project_selection = ProjectVersion.project.identifier == project
        else:
            project_selection = ProjectVersion.project == project

        return ReadQuery[StagingAllocation](
            StagingAllocation.select().where(project_selection)
        ).execute()

    def find_staging_allocation(self, project):
        return ReadQuery[StagingAllocation](
            StagingAllocation.select().where(
                StagingAllocation.project_version == project
            )
        ).find_one()

    def delete_staging_allocation(self, project):
        # Ignore spurious warning
        # pylint: disable=no-value-for-parameter
        DeleteQuery[StagingAllocation](
            StagingAllocation.delete().where(
                StagingAllocation.project_version == project
            )
        ).execute()


class DataAccessRDBMS(DataAccess):
    """Implementation of the `DataAccess` interface for RDBMS persistence."""

    def users(self):
        return _UserDAOImpl()

    def projects(self):
        return _ProjectDAOImpl()
