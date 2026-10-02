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

from typing import Final

from raven.fathom.base import TypeCheck
from raven.fathom.base import Project
from raven.fathom.base import User
from raven.fathom.base import UserState
from raven.fathom.server.dao import DataAccess
from raven.fathom.server.dao import FailedDeleteQueryException
from raven.fathom.server.models import User as UserModel
from raven.fathom.server.models import UserRole
from raven.fathom.server.security import UserAuthenticator


SYSTEM_USER_IDENTIFIER: Final[str] = "fathom"

SYSTEM_USER_NAME: Final[str] = "Fathom System User"


class UserManager:
    """Provides methods to manage application users."""

    def __init__(self):
        """Initializes a new `UserManager` instance."""
        self._ds = DataAccess.instance()
        self._authenticator = UserAuthenticator()

    def is_setup_complete(self) -> bool:
        """Indicates whether the server bootstrap has been completed."""
        return self.find_system_user_record() is not None

    def find_system_user_record(self) -> UserModel | None:
        """Returns the configured system user record, if one exists."""
        for user in self._ds.users().read_all():
            if UserRole(str(user.role)) == UserRole.SYSTEM:
                return user

        return None

    def get_user_role(self, identifier: str) -> UserRole:
        """Resolves the stored role of a managed user."""
        user = self._ds.users().find_by_identifier(identifier)
        if user is None:
            raise ValueError(f"User '{identifier}' does not exist")

        return UserRole(str(user.role))

    def create_system_user(self, user: User):
        """Creates the one-time system user for the server bootstrap."""
        TypeCheck.require_arg(user.password, str)
        if not user.password:
            raise ValueError("User password must not be empty")

        if self.is_setup_complete():
            raise ValueError("The server has already been set up")

        user_record = UserModel(
            identifier=SYSTEM_USER_IDENTIFIER,
            name=SYSTEM_USER_NAME,
            password=user.password,
            role=UserRole.SYSTEM,
            state=UserState.ACTIVE,
        )
        self._authenticator.constitute_password_authentication(user_record)
        self._ds.users().create_new_user(user_record, admin_privileges=True)
        user.identifier = SYSTEM_USER_IDENTIFIER
        user.name = str(user_record.name)
        user.password = ""
        user.is_admin = True
        user.state = UserState.ACTIVE

    def create_user(self, user: User):
        """Creates a new Fathom user on the server.

        The role of the new user is determined by the attributes of
        the `User` object. If `is_admin` is `True`, the user will be
        created with the administrator role, otherwise the user will
        have a regular user role.

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

        settings = self._ds.settings().find_server_settings()
        if not settings.shared_secret:
            raise ValueError(
                "Cannot create new user. "
                "No shared secret set "
                f"for organisation '{settings.organisation_name}'"
            )

        user_record = UserModel(
            identifier=user.identifier,
            name=name,
            password=settings.shared_secret,
            role=(
                UserRole.ADMINISTRATOR
                if user.is_admin else UserRole.USER
            ),
            state=str(UserState.ONBOARDING),
        )
        self._authenticator.constitute_password_authentication(user_record)
        self._ds.users().create_new_user(
            user_record,
            admin_privileges=user.is_admin
        )

    def sign_up_user(self, user: User):
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
        user.name = user_record.name
        user.password = "" # Evict
        user.is_admin = self._role_has_admin_privileges(user_record.role)
        user.state = UserState.ACTIVE

    def list_users(self) -> list[User]:
        """Lists all users registered in the server backend.

        Returns:
            list: A `list` of `User` objects managed by the Fathom server.
        """
        result = []
        for user in self._ds.users().read_all():
            role = UserRole(str(user.role))
            if role != UserRole.SYSTEM:
                result.append(
                    User(
                        identifier=str(user.identifier),
                        name=str(user.name),
                        is_admin=self._role_has_admin_privileges(role),
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
            user_record = self._ds.users().find_by_identifier(user.identifier)
            if user_record is None:
                raise ValueError(
                    f"Failed to delete user '{user.identifier}'"
                )

            if UserRole(str(user_record.role)) == UserRole.SYSTEM:
                raise ValueError("The system user cannot be deleted")

            self._ds.users().delete_by_identifier(user.identifier)
        except FailedDeleteQueryException as ex:
            raise ValueError(
                f"Failed to delete user '{user.identifier}'"
            ) from ex

    def _role_has_admin_privileges(self, role: UserRole | str) -> bool:
        role = UserRole(str(role))
        return role.has_administrative_privileges()

    def assign_user_to_project(self, user: User, project: Project):
        """Assigns an existing user to an existing project.

        Args:
            user (User): The user to assign.
            project (Project): The project to assign the user to.

        Raises:
            ValueError: If the given user or project is invalid.
        """
        TypeCheck.require_arg(user.identifier, str)
        TypeCheck.require_arg(project.identifier, str)
        if not user.identifier:
            raise ValueError("User identifier must not be empty")

        if not project.identifier:
            raise ValueError("Project identifier must not be empty")

        user_record = self._ds.users().find_by_identifier(user.identifier)
        if user_record is None:
            raise ValueError(f"User '{user.identifier}' does not exist")

        project_record = self._ds.projects().find_by_identifier(
            project.identifier
        )
        if project_record is None:
            raise ValueError(f"Project '{project.identifier}' does not exist")

        assigned_projects = self._ds.projects().find_all_assigned_to_user(
            user_record
        )
        if any(
            record.id == project_record.id # type: ignore
            for record in assigned_projects
        ):
            raise ValueError(
                f"User '{user.identifier}' is already assigned "
                f"to project '{project.identifier}'"
            )

        self._ds.projects().assign_user_to_project(user_record, project_record)

    def unassign_user_from_project(self, user: User, project: Project):
        """Removes a user's assignment from an existing project.

        Args:
            user (User): The user to unassign.
            project (Project): The project to remove the user from.

        Raises:
            ValueError: If the given user or project is invalid.
        """
        TypeCheck.require_arg(user.identifier, str)
        TypeCheck.require_arg(project.identifier, str)
        if not user.identifier:
            raise ValueError("User identifier must not be empty")

        if not project.identifier:
            raise ValueError("Project identifier must not be empty")

        user_record = self._ds.users().find_by_identifier(user.identifier)
        if user_record is None:
            raise ValueError(f"User '{user.identifier}' does not exist")

        project_record = self._ds.projects().find_by_identifier(
            project.identifier
        )
        if project_record is None:
            raise ValueError(f"Project '{project.identifier}' does not exist")

        assigned_projects = self._ds.projects().find_all_assigned_to_user(
            user_record
        )
        if all(
            record.id != project_record.id # type: ignore
            for record in assigned_projects
        ):
            raise ValueError(
                f"User '{user.identifier}' is not assigned "
                f"to project '{project.identifier}'"
            )

        self._ds.projects().unassign_user_from_project(
            user_record,
            project_record,
        )
