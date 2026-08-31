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
"""Data access object declaration for user-related data."""

from abc import abstractmethod
from typing import Optional

from raven.fathom.server.dao.base import DataAccessObject
from raven.fathom.server.models import User, UserPermission, AuthDeployment


class UserDAO(DataAccessObject):
    """A data access object for user-related data."""

    @abstractmethod
    def find_by_identifier(self, identifier: str) -> Optional[User]:
        """Gets the user record with the specified identifier.

        Args:
            identifier (str): The unique identifier of the user to get.

        Returns:
            User: The `User` object with the specified identifier,
                or `None` if no such user can be found.
        """

    @abstractmethod
    def find_permission(self, user: User) -> UserPermission:
        """Gets the user's permission record.

        Args:
            user (User): The user record to get the permission record for.

        Returns:
            UserPermission: The `UserPermission` object associated with the
                given user.

        Raises:
            IncoherentDatastoreStateException: If the permission record
                does not exist.
        """

    @abstractmethod
    def find_deployment_authorization_by_token(
        self,
        token: str
    ) -> Optional[AuthDeployment]:
        """Finds the deployment authorization with the specified token.

        Args:
            token (str): The secret token string corresponding to
                the deployment authorization to find.

        Returns:
            AuthDeployment: The `AuthDeployment` object for the specified
                token, or `None` if no such authorization can be found.
        """
