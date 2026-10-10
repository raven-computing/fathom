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
from raven.fathom.server.dao import FailedCreateQueryException
from raven.fathom.server.dao import FailedReadQueryException
from raven.fathom.server.dao import FailedUpdateQueryException
from raven.fathom.server.dao import FailedDeleteQueryException
from raven.fathom.server.models import User as UserModel
from raven.fathom.server.models import UserRole
from raven.fathom.server.security import UserAuthenticator
from raven.fathom.server.core.exceptions import DomainException


class UserManagementException(DomainException):
    """Base class for user-management domain failures."""


class InvalidUserRequestException(UserManagementException):
    """A precondition for a requested operation was not met or some input
    given to a requested operation was invalid.
    """


class UserNotFoundException(InvalidUserRequestException):
    """An operation was requested for a user that does not actually exist."""


class UserAlreadyExistsException(InvalidUserRequestException):
    """An attempt was made to create a user that already exists."""


class UserStateException(UserManagementException):
    """A user is in an invalid state or the requested operation is illegal
    in the user's current state.
    """


class UserInternalException(UserManagementException):
    """Infrastructure has failed unexpectedly.

    Signals a lower-level internal system error that is not a caller mistake.
    """


SYSTEM_USER_IDENTIFIER: Final[str] = "fathom"

SYSTEM_USER_NAME: Final[str] = "Fathom System User"


class UserManager:
    """Provides methods to manage application users."""

    def __init__(self, authenticator: UserAuthenticator):
        """Initializes a new `UserManager` instance.

        Args:
            authenticator (UserAuthenticator): The object to be used
                for delegating the handling of security-related authentication
                details to.
        """
        self._ds = DataAccess.instance()
        self._authenticator = authenticator

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
            raise UserNotFoundException(f"User '{identifier}' does not exist")

        return UserRole(str(user.role))

    def create_system_user(self, user: User):
        """Creates the one-time system user for the server bootstrap.
        
        Args:
            user (User): The User object representing the system user to create.

        Raises:
            UserManagementException: If the system user cannot be created.
        """
        TypeCheck.require_arg(user.password, str)
        if not user.password:
            raise InvalidUserRequestException("User password must not be empty")

        if self.is_setup_complete():
            raise UserManagementException("The server has already been set up")

        user_record = UserModel(
            identifier=SYSTEM_USER_IDENTIFIER,
            name=SYSTEM_USER_NAME,
            password=user.password,
            role=UserRole.SYSTEM,
            state=UserState.ACTIVE,
        )
        self._authenticator.constitute_password_authentication(user_record)
        try:
            self._ds.users().create_new_user(user_record)
        except FailedCreateQueryException as ex:
            raise UserManagementException(
                f"Failed to create system user '{user_record.identifier}'. "
                "An internal error has occurred."
            ) from ex

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
            UserManagementException: If the given user cannot be created.
        """
        TypeCheck.require_arg(user.identifier, str)
        if not user.identifier:
            raise InvalidUserRequestException(
                "Cannot create user. User identifier must not be empty"
            )

        if self._ds.users().find_by_identifier(user.identifier) is not None:
            raise UserAlreadyExistsException(
                f"Cannot create user '{user.identifier}'. User already exists"
            )

        name = user.name
        if not name:
            name = user.identifier

        if user.state != UserState.ONBOARDING:
            raise UserStateException(
                f"Cannot create user '{user.identifier}'. User must be in "
                f"initial state {UserState.ONBOARDING} in order to be created"
            )

        settings = self._ds.settings().find_server_settings()
        if not settings.shared_secret:
            raise UserManagementException(
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
        try:
            self._ds.users().create_new_user(user_record)
        except FailedCreateQueryException as ex:
            raise UserManagementException(
                f"Failed to create user '{user_record.identifier}'. "
                "An internal error has occurred."
            ) from ex

    def sign_up_user(self, user: User):
        """Sets the initial password for an onboarding user.

        Args:
            user (User): The User object for which
                to complete the setup procedure.

        Raises:
            UserManagementException: If the setup procedure cannot be
                completed or the given user is invalid.
        """
        identifier = user.identifier
        password = user.password
        TypeCheck.require_arg(identifier, str)
        TypeCheck.require_arg(password, str)
        if not identifier:
            raise InvalidUserRequestException(
                "User sign-up failed.User identifier must not be empty"
            )

        if not password:
            raise InvalidUserRequestException("User password must not be empty")

        user_record = self._ds.users().find_by_identifier(identifier)
        if user_record is None:
            raise UserNotFoundException(f"User '{identifier}' does not exist")

        if str(user_record.state) != str(UserState.ONBOARDING):
            raise UserStateException(
                f"User '{identifier}' has already been initialized"
            )

        user_record.password = password
        user_record.state = UserState.ACTIVE
        self._authenticator.constitute_password_authentication(user_record)
        try:
            self._ds.users().update(user_record)
        except FailedUpdateQueryException as ex:
            raise UserManagementException(
                f"Failed to update user '{user_record.identifier}'. "
                "An internal error has occurred."
            ) from ex

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
        try:
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
        except FailedReadQueryException as ex:
            raise UserManagementException(
                "Failed to list users. An internal error has occurred."
            ) from ex

        return result

    def delete_user(self, user: User):
        """Deletes the Fathom user and associated records.

        Args:
            user (User): The base User object which represents the Fathom
                user to delete from the server backend.

        Raises:
            UserManagementException: If the given user is invalid or could
                not be deleted.
        """
        TypeCheck.require_arg(user.identifier, str)
        if not user.identifier:
            raise InvalidUserRequestException(
                "Cannot delete user. User identifier must not be empty"
            )

        try:
            user_record = self._ds.users().find_by_identifier(user.identifier)
            if user_record is None:
                raise UserNotFoundException(
                    f"Failed to delete user '{user.identifier}'. "
                    "User does not exist."
                )

            if UserRole(str(user_record.role)) == UserRole.SYSTEM:
                raise UserStateException("The system user cannot be deleted")

            self._ds.users().delete_by_identifier(user.identifier)
        except FailedDeleteQueryException as ex:
            raise UserInternalException(
                f"Failed to delete user '{user.identifier}'. "
                "An internal error has occurred."
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
            UserManagementException: If the given user or project is invalid.
        """
        TypeCheck.require_arg(user.identifier, str)
        TypeCheck.require_arg(project.identifier, str)
        if not user.identifier:
            raise InvalidUserRequestException(
                "Cannot assign user to project. "
                "User identifier must not be empty"
            )

        if not project.identifier:
            raise InvalidUserRequestException(
                "Cannot assign user to project. "
                "Project identifier must not be empty"
            )

        user_record = self._ds.users().find_by_identifier(user.identifier)
        if user_record is None:
            raise UserNotFoundException(
                "Cannot assign user to project. "
                f"User '{user.identifier}' does not exist"
            )

        project_record = self._ds.projects().find_by_identifier(
            project.identifier
        )
        if project_record is None:
            raise InvalidUserRequestException(
                "Cannot assign user to project. "
                f"Project '{project.identifier}' does not exist"
            )

        assigned_projects = self._ds.projects().find_all_assigned_to_user(
            user_record
        )
        if any(
            record.id == project_record.id # type: ignore
            for record in assigned_projects
        ):
            raise UserManagementException(
                "Cannot assign user to project. "
                f"User '{user.identifier}' is already assigned "
                f"to project '{project.identifier}'"
            )

        try:
            self._ds.projects().assign_user_to_project(
                user_record, project_record
            )
        except FailedUpdateQueryException as ex:
            raise UserManagementException(
                f"Cannot assign user '{user.identifier}' "
                f"to project '{project.identifier}'. "
                "An internal error has occurred."
            ) from ex

    def unassign_user_from_project(self, user: User, project: Project):
        """Removes a user's assignment from an existing project.

        Args:
            user (User): The user to unassign.
            project (Project): The project to remove the user from.

        Raises:
            UserManagementException: If the given user or project is invalid.
        """
        TypeCheck.require_arg(user.identifier, str)
        TypeCheck.require_arg(project.identifier, str)
        if not user.identifier:
            raise InvalidUserRequestException(
                "Cannot unassign user from project. "
                "User identifier must not be empty"
            )

        if not project.identifier:
            raise InvalidUserRequestException(
                "Cannot unassign user from project. "
                "Project identifier must not be empty"
            )

        user_record = self._ds.users().find_by_identifier(user.identifier)
        if user_record is None:
            raise UserNotFoundException(
                "Cannot unassign user from project. "
                f"User '{user.identifier}' does not exist"
            )

        project_record = self._ds.projects().find_by_identifier(
            project.identifier
        )
        if project_record is None:
            raise UserManagementException(
                "Cannot unassign user from project. "
                f"Project '{project.identifier}' does not exist"
            )

        assigned_projects = self._ds.projects().find_all_assigned_to_user(
            user_record
        )
        if all(
            record.id != project_record.id # type: ignore
            for record in assigned_projects
        ):
            raise UserManagementException(
                "Cannot unassign user from project. "
                f"User '{user.identifier}' is not assigned "
                f"to project '{project.identifier}'"
            )

        try:
            self._ds.projects().unassign_user_from_project(
                user_record,
                project_record,
            )
        except FailedUpdateQueryException as ex:
            raise UserManagementException(
                f"Cannot unassign user '{user.identifier}' "
                f"from project '{project.identifier}'. "
                "An internal error has occurred."
            ) from ex
