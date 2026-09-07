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
"""Implementation of the data access API using mocks for testing."""

from raven.fathom.server.dao import DataAccess
from raven.fathom.server.models import User
from raven.fathom.server.models import Project
from raven.fathom.server.models import UserPermission

from tests.unit.mocks import Mock


class DataMock(Mock):
    """Mock object for generic data requests."""


class UserDAOMock(Mock):
    """Mock object for the `UserDAO`."""


class ProjectDAOMock(Mock):
    """Mock object for the `ProjectDAO`."""


class DataAccessMock(DataAccess):
    """Implementation of the `DataAccess` interface for testing purposes."""

    DATA_MOCK = DataMock()

    USER_DAO_MOCK = UserDAOMock()

    PROJECT_DAO_MOCK = ProjectDAOMock()

    def data(self, model):
        return DataAccessMock.DATA_MOCK

    def users(self):
        return DataAccessMock.USER_DAO_MOCK

    def projects(self):
        return DataAccessMock.PROJECT_DAO_MOCK

    def set_up_deployment_authorization_mocks(self, valid_intent):
        """Setup method for deployment authorization tests."""
        valid_user = valid_intent.user
        valid_project = valid_intent.project
        stored_user = User(
            identifier=valid_user.identifier,
            name=valid_user.name,
        )
        self.users().find_by_identifier.return_value = stored_user
        self.users().find_permission.return_value = UserPermission(
            user=stored_user,
            allow_overwrite=True,
            is_admin=False,
        )
        stored_project = Project(
            identifier=valid_project.identifier,
            name=valid_project.name,
            description=valid_project.description,
            latest_version=valid_project.version.identifier,
        )
        self.projects().find_by_identifier.return_value = stored_project
        self.projects().find_all_assigned_to_user.return_value = [
            stored_project,
        ]

    @staticmethod
    def reset():
        """Resets the state of the mock data.UserDAOMock"""
        DataAccessMock.DATA_MOCK  = DataMock()
        DataAccessMock.USER_DAO_MOCK  = UserDAOMock()
        DataAccessMock.PROJECT_DAO_MOCK = ProjectDAOMock()
