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
"""Management of dedicated application users."""

from raven.fathom.base import TypeCheck
from raven.fathom.base import User
from raven.fathom.base import UserState
from raven.fathom.base import USER_ONBOARDING_SHARED_SECRET
from raven.fathom.server.dao import DataAccess
from raven.fathom.server.dao import FailedDeleteQueryException
from raven.fathom.server.models import User as UserModel
from raven.fathom.server.security import UserAuthenticator


class UserManager:
    """Provides methods to manage application users."""

    def __init__(self):
        """Initializes a new `UserManager` instance."""
        self._ds = DataAccess.instance()
        self._authenticator = UserAuthenticator()

    def create_user(self, user: User):
        """Creates a new Fathom user on the server.

        Args:
            user (User): The User object to create in the server backend.

        Raises:
            ValueError: If the given user cannot be created.
        """
        TypeCheck.require_arg(user.identifier, str)
        if not user.identifier:
            raise ValueError("User identifier must not be empty")

        if self._ds.users().find_by_identifier(user.identifier) is not None:
            raise ValueError(f"User '{user.identifier}' already exists")

        name = user.name
        if not name:
            name = user.identifier

        if user.state != UserState.ONBOARDING:
            raise ValueError(
                f"User '{user.identifier}' must be in "
                f"initial state {UserState.ONBOARDING} in order to be created"
            )

        user_record = UserModel(
            identifier=user.identifier,
            name=user.name,
            password=USER_ONBOARDING_SHARED_SECRET,
            state=str(UserState.ONBOARDING),
        )
        self._authenticator.constitute_password_authentication(user_record)
        self._ds.users().create_new_user(
            user_record,
            admin_privileges=user.is_admin
        )

    def setup_user(self, user: User):
        """Sets the initial password for an onboarding user.

        Args:
            user (User): The User object for which
                to complete the setup procedure.

        Raises:
            ValueError: If the setup procedure cannot be completed
                or the given user is invalid.
        """
        identifier = user.identifier
        password = user.password
        TypeCheck.require_arg(identifier, str)
        TypeCheck.require_arg(password, str)
        if not identifier:
            raise ValueError("User identifier must not be empty")

        if not password:
            raise ValueError("User password must not be empty")

        user_record = self._ds.users().find_by_identifier(identifier)
        if user_record is None:
            raise ValueError(f"User '{identifier}' does not exist")

        if str(user_record.state) != str(UserState.ONBOARDING):
            raise ValueError(
                f"User '{identifier}' has already been initialized"
            )

        user_record.password = password
        user_record.state = UserState.ACTIVE
        self._authenticator.constitute_password_authentication(user_record)
        self._ds.users().update(user_record)
        permission = self._ds.users().find_permission(user_record)
        user.name = user_record.name
        user.password = "" # Evict
        user.is_admin = permission.is_admin
        user.state = UserState.ACTIVE

    def list_users(self) -> list[User]:
        """Lists all users registered in the server backend.

        Returns:
            list: A `list` of `User` objects managed by the Fathom server.
        """
        result = []
        for user in self._ds.users().read_all():
            permission = self._ds.users().find_permission(user)
            result.append(
                User(
                    identifier=str(user.identifier),
                    name=str(user.name),
                    is_admin=bool(permission.is_admin),
                    state=UserState(str(user.state)),
                )
            )

        return result

    def delete_user(self, user: User):
        """Deletes the Fathom user and associated records.

        Args:
            user (User): The base User object which represents the Fathom
                user to delete from the server backend.

        Raises:
            ValueError: If the given user is invalid or could not be deleted.
        """
        TypeCheck.require_arg(user.identifier, str)
        if not user.identifier:
            raise ValueError("User identifier must not be empty")

        try:
            self._ds.users().delete_by_identifier(user.identifier)
        except FailedDeleteQueryException as ex:
            raise ValueError(
                f"Failed to delete user '{user.identifier}'"
            ) from ex
