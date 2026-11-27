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

from enum import StrEnum

from raven.fathom.base import TypeCheck
from raven.fathom.base import User
from raven.fathom.base import UserState
from raven.fathom.server.dao import DataAccess
from raven.fathom.server.dao import FailedCreateQueryException
from raven.fathom.server.dao import FailedReadQueryException
from raven.fathom.server.dao import FailedUpdateQueryException
from raven.fathom.server.dao import FailedDeleteQueryException
from raven.fathom.server.dao import IncoherentDatastoreStateException
from raven.fathom.server.models import User as UserModel
from raven.fathom.server.models import UserRole
from raven.fathom.server.models import SYSTEM_USER_NAME
from raven.fathom.server.security import UserAuthenticator
from raven.fathom.server.core.exceptions import FathomServerException


class UserManagementException(FathomServerException):
    """Base class for user-management application failures."""


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


class UserPermissionKey(StrEnum):
    """Supported user permission keys."""

    ALLOW_OVERWRITE = "allow_overwrite"


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
        """Indicates whether the server bootstrap has been completed.

        Setup is complete when server settings exist, the system user has
        been created, and at least one Administrator account is present
        (in ACTIVE or RESET state).
        """
        try:
            settings = self._ds.settings().find_server_settings()
        except IncoherentDatastoreStateException:
            return False

        if settings is None:
            return False

        if not self._system_user_exists():
            return False

        return self._has_active_or_reset_administrator()

    def _system_user_exists(self) -> bool:
        for user in self._ds.users().read_all():
            if user.role == UserRole.SYSTEM:
                return True

        return False

    def _has_active_or_reset_administrator(self) -> bool:
        for user in self._ds.users().read_all():
            if (
                user.role == UserRole.ADMINISTRATOR
                and user.state in (UserState.ACTIVE, UserState.RESET)
            ):
                return True

        return False

    def _has_active_administrator(self) -> bool:
        for user in self._ds.users().read_all():
            if (
                user.role == UserRole.ADMINISTRATOR
                and user.state == UserState.ACTIVE
            ):
                return True

        return False

    def create_system_user(self, identifier: str, password: str):
        """Creates the one-time system user for local administrative access.

        The system user is never accessible over the network.

        Args:
            identifier (str): The unique identifier for the system user.
            password (str): The plain-text password for the system user.

        Raises:
            UserManagementException: If the system user cannot be created.
        """
        if not identifier:
            raise InvalidUserRequestException(
                "System user identifier must not be empty"
            )

        if not password:
            raise InvalidUserRequestException(
                "System user password must not be empty"
            )

        if self._system_user_exists():
            raise UserManagementException(
                "A system user already exists. "
                "The server has already been set up."
            )

        user_record = UserModel(
            identifier=identifier,
            name=SYSTEM_USER_NAME,
            password=password,
            role=UserRole.SYSTEM,
            state=UserState.ACTIVE,
        )
        self._authenticator.constitute_password_authentication(user_record)
        try:
            self._ds.users().create_new_user(user_record)
        except FailedCreateQueryException as ex:
            raise UserInternalException(
                f"Failed to create system user '{identifier}'. "
                "An internal error has occurred."
            ) from ex

    def reset_user(self, identifier: str):
        """Resets a user's credentials and places the account in RESET state.

        The user record is stamped with the current shared-secret hash,
        identical to the ONBOARDING flow. The affected user must re-establish
        their credentials by running the client sign-up procedure using the
        current shared secret before they can log in again.

        Args:
            identifier (str): The identifier of the user to reset.

        Raises:
            UserManagementException: If the user cannot be reset.
        """
        if not identifier:
            raise InvalidUserRequestException(
                "Cannot reset user. User identifier must not be empty"
            )

        user_record = self._ds.users().find_by_identifier(identifier)
        if user_record is None:
            raise UserNotFoundException(
                f"Cannot reset user '{identifier}'. User does not exist."
            )

        if user_record.role == UserRole.SYSTEM:
            raise UserStateException(
                "The system user password cannot be reset through this "
                "command. To recover a lost system user password, the "
                "stored credential must be updated directly in the database."
            )

        settings = self._ds.settings().find_server_settings()
        user_record.password = settings.shared_secret
        user_record._state = UserState.RESET  # pylint: disable=protected-access
        self._authenticator.constitute_password_authentication(user_record)
        try:
            self._ds.users().update(user_record)
        except FailedUpdateQueryException as ex:
            raise UserInternalException(
                f"Failed to reset user '{identifier}'. "
                "An internal error has occurred."
            ) from ex

    def rotate_shared_secret(self, new_secret: str):
        """Replaces the organisation's shared signup secret.

        Existing active users are unaffected. Users in ONBOARDING or RESET
        state who were stamped with the previous secret will no longer be
        able to complete sign-up and must be reset again to receive the
        updated secret.

        Args:
            new_secret (str): The new shared secret to set.

        Raises:
            UserManagementException: If the secret cannot be updated.
        """
        if not new_secret:
            raise InvalidUserRequestException(
                "Shared secret must not be empty"
            )

        settings = self._ds.settings().find_server_settings()
        settings.shared_secret = new_secret
        try:
            self._ds.settings().update(settings)
        except FailedUpdateQueryException as ex:
            raise UserInternalException(
                "Failed to update shared secret. "
                "An internal error has occurred."
            ) from ex

    def create_initial_admin(self, identifier: str, password: str):
        """Creates the first active Administrator during server setup.

        This method bypasses the normal onboarding flow and creates an
        immediately active Administrator. It must only be called once
        during the initial setup procedure.

        Args:
            identifier (str): The unique identifier for the administrator.
            password (str): The plain-text password for the administrator.

        Raises:
            UserManagementException: If the administrator cannot be created.
        """
        if not identifier:
            raise InvalidUserRequestException(
                "Administrator identifier must not be empty"
            )

        if not password:
            raise InvalidUserRequestException(
                "Administrator password must not be empty"
            )

        if self._ds.users().find_by_identifier(identifier) is not None:
            raise UserAlreadyExistsException(
                f"Cannot create administrator '{identifier}'. "
                "User already exists"
            )

        user_record = UserModel(
            identifier=identifier,
            name=identifier,
            password=password,
            role=UserRole.ADMINISTRATOR,
            state=UserState.ACTIVE,
        )
        self._authenticator.constitute_password_authentication(user_record)
        try:
            self._ds.users().create_new_user(user_record)
        except FailedCreateQueryException as ex:
            raise UserInternalException(
                f"Failed to create initial administrator '{identifier}'. "
                "An internal error has occurred."
            ) from ex

    def get_user_role(self, identifier: str) -> UserRole:
        """Resolves the stored role of a managed user."""
        user = self._ds.users().find_by_identifier(identifier)
        if user is None:
            raise UserNotFoundException(f"User '{identifier}' does not exist")

        return user.role

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
            state=UserState.ONBOARDING,
        )
        self._authenticator.constitute_password_authentication(user_record)
        try:
            self._ds.users().create_new_user(user_record)
        except FailedCreateQueryException as ex:
            raise UserInternalException(
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
                "User sign-up failed. User identifier must not be empty"
            )

        if not password:
            raise InvalidUserRequestException("User password must not be empty")

        user_record = self._ds.users().find_by_identifier(identifier)
        if user_record is None:
            raise UserNotFoundException(f"User '{identifier}' does not exist")

        if user_record.state not in (UserState.ONBOARDING, UserState.RESET):
            raise UserStateException(
                f"User '{identifier}' has already been initialized"
            )

        user_record.password = password
        user_record.set_active()
        self._authenticator.constitute_password_authentication(user_record)
        try:
            self._ds.users().update(user_record)
        except FailedUpdateQueryException as ex:
            raise UserInternalException(
                f"Failed to update user '{user_record.identifier}'. "
                "An internal error has occurred."
            ) from ex

        user.name = user_record.name
        user.password = "" # Evict
        user.is_admin = user_record.role.has_administrative_privileges()
        user.state = UserState.ACTIVE

    def list_users(self) -> list[User]:
        """Lists all users registered in the server backend.

        Returns:
            list: A `list` of `User` objects managed by the Fathom server.
        """
        result = []
        try:
            for user in self._ds.users().read_all():
                role = user.role
                if role != UserRole.SYSTEM:
                    result.append(
                        User(
                            identifier=str(user.identifier),
                            name=str(user.name),
                            is_admin=role.has_administrative_privileges(),
                            state=UserState(str(user.state)),
                        )
                    )
        except FailedReadQueryException as ex:
            raise UserInternalException(
                "Failed to list users. An internal error has occurred."
            ) from ex

        return result

    def get_user_permission(
        self,
        user: User,
        permission_key: UserPermissionKey,
    ) -> str:
        """Gets a permission value for a registered Fathom user.

        Args:
            user (User): The user whose permission should be read.
            permission_key (UserPermissionKey): The permission key to read.

        Returns:
            str: The current value of the requested permission.

        Raises:
            UserManagementException: If the user or permission is invalid.
        """
        TypeCheck.require_arg(permission_key, UserPermissionKey)
        if not user.identifier:
            raise InvalidUserRequestException(
                "Cannot get user permission. User identifier must not be empty"
            )

        user_record = self._ds.users().find_by_identifier(user.identifier)
        if user_record is None:
            raise UserNotFoundException(
                f"User '{user.identifier}' does not exist"
            )

        if user_record.role == UserRole.SYSTEM:
            raise UserStateException(
                "Cannot get permissions of a system user"
            )

        permission = self._ds.users().find_permission(user_record)
        return str(permission.allow_overwrite)

    def set_user_permission(
        self,
        user: User,
        permission_key: UserPermissionKey,
        value: str,
    ):
        """Sets a permission for a registered Fathom user.

        Args:
            user (User): The user whose permission should be changed.
            permission_key (UserPermissionKey): The permission key to set.
            value (str): The new permission value.

        Raises:
            UserManagementException: If the user or permission is invalid or
                the update fails.
        """
        TypeCheck.require_arg(permission_key, UserPermissionKey)
        if not user.identifier:
            raise InvalidUserRequestException(
                "Cannot set user permission. User identifier must not be empty"
            )

        user_record = self._ds.users().find_by_identifier(user.identifier)
        if user_record is None:
            raise UserNotFoundException(
                f"User '{user.identifier}' does not exist"
            )

        if user_record.role == UserRole.SYSTEM:
            raise UserStateException(
                "Permissions of a system user cannot be changed"
            )

        permission = self._ds.users().find_permission(user_record)
        if permission_key == UserPermissionKey.ALLOW_OVERWRITE:
            permission.allow_overwrite = self._convert_bool_permission_value(
                permission_key,
                value
            )
        else:
            raise UserInternalException(
                f"Invalid permission '{permission_key}'"
            )

        try:
            self._ds.users().update_permission(permission)
        except FailedUpdateQueryException as ex:
            raise UserInternalException(
                f"Failed to set permission '{permission_key}' "
                f"for user '{user.identifier}'. "
                "An internal error has occurred."
            ) from ex

    def delete_user(self, user: User, requesting_user_id: str = ""):
        """Deletes the Fathom user and associated records.

        Args:
            user (User): The base User object which represents the Fathom
                user to delete from the server backend.
            requesting_user_id (str): The identifier of the user making
                the deletion request. Used to enforce self-deletion invariant.

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

            if user_record.role == UserRole.SYSTEM:
                raise UserStateException("The system user cannot be deleted")

            if requesting_user_id and user.identifier == requesting_user_id:
                raise UserStateException(
                    f"User '{user.identifier}' cannot delete themselves"
                )

            if user_record.role == UserRole.ADMINISTRATOR:
                self._ensure_not_last_administrator(user.identifier)

            self._ds.users().delete_by_identifier(user.identifier)
        except FailedDeleteQueryException as ex:
            raise UserInternalException(
                f"Failed to delete user '{user.identifier}'. "
                "An internal error has occurred."
            ) from ex

    def _ensure_not_last_administrator(self, identifier: str):
        remaining_admin_count = sum(
            1
            for u in self._ds.users().read_all()
            if u.role == UserRole.ADMINISTRATOR
            and u.state in (UserState.ACTIVE, UserState.RESET)
            and str(u.identifier) != identifier
        )
        if remaining_admin_count == 0:
            raise UserStateException(
                f"Cannot delete administrator '{identifier}'. "
                "At least one active administrator must remain."
            )

    def _convert_bool_permission_value(self, permission_key, value):
        normalized_value = value.upper()
        if normalized_value in ("ON", "YES", "1", "TRUE"):
            permission_value = True
        elif normalized_value in ("OFF", "NO", "0", "FALSE"):
            permission_value = False
        else:
            raise InvalidUserRequestException(
                    f"Invalid value '{value}' for permission "
                    f"'{permission_key}'. Must be either 'ON' or 'OFF'"
                )

        return permission_value
