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
"""Authentication facilities."""

from typing import Optional, Final

from raven.fathom.base import TypeCheck
from raven.fathom.base import User as BaseUser, UserState
from raven.fathom.base import ClientRequest
from raven.fathom.base import ClientAuthentication
from raven.fathom.base import EntropySource
from raven.fathom.base import ProcessingException
from raven.fathom.server.dao import DataAccess
from raven.fathom.server.models import User
from raven.fathom.server.security._hash import PasswordHasher
from raven.fathom.server.security._hash import StoredPasswordHash
from raven.fathom.server.security._hash import PasswordValidation


PASSWORD_ENCODING: Final = "UTF-8"

PASSWORD_SALT_LENGTH: Final = 16


def _check_client_auth_types(request: ClientRequest):
    """Safety check for username-password-combination in a made request."""
    TypeCheck.require_arg(request, ClientRequest)
    auth = request.authentication
    if auth is None:
        raise ProcessingException("Client has no authentication set")

    TypeCheck.require(auth, ClientAuthentication)
    TypeCheck.require(auth.username, str)
    TypeCheck.require(auth.password, str)
    if not auth.username:
        raise ProcessingException(
            "Client authentication username must not be empty"
        )

    if not auth.password:
        raise ProcessingException(
            "Client authentication password must not be empty"
        )


def _check_user_record_types(user: User):
    """Safety check for username-password-combination within a user record."""
    TypeCheck.require_arg(user, User)
    TypeCheck.require(user.identifier, str)
    if not user.identifier:
        raise ProcessingException("User identifier must not be empty")

    TypeCheck.require(user.password, str)
    if not user.password:
        raise ProcessingException("User password must not be empty")


class UserAuthentication:
    """The result object of a requested user authentication."""

    def __init__(self, user: Optional[User], is_authenticated: bool):
        self._internal_user = user
        self._internal_auth = is_authenticated

    @property
    def user_record(self) -> Optional[User]:
        """The identified user of an authentication request, as a `User`.

        May be `None` if no user could be identified from a submitted request.
        """
        return self._internal_user

    def is_authenticated(self) -> bool:
        """Indicates whether a user could be successfully authenticated.

        Returns:
            bool: `True` if the user could be authenticated, `False` otherwise.
        """
        return self._internal_auth


class UserAuthenticator:
    """Handles user authentication."""

    def __init__(self):
        """Initializes a new `UserAuthenticator` instance."""
        self._ds = DataAccess.instance()

    def constitute_password_authentication(self, user: User):
        """Sets up authentication via a password for the given user.

        Args:
            user (User): The user record with a valid identifier and password.

        Raises:
            ProcessingException: If the user record does not have a valid
                identifier or password set.
        """
        _check_user_record_types(user)
        hasher = PasswordHasher.get_default()
        salt = self._generate_password_salt()
        password_hash = hasher.digest(
            user.password.encode(PASSWORD_ENCODING), # type: ignore
            salt
        )
        self._assign_password(
            user,
            StoredPasswordHash(
                hasher.specification(),
                salt.hex(),
                password_hash.hex()
            )
        )

    def authenticate_client(
        self,
        request: ClientRequest
    ) -> UserAuthentication:
        """Authenticates the given client request.

        Once successfully authenticated, the `ClientAuthentication.password`
        field value in the given `ClientRequest` is redacted and can
        no longer be used.

        Args:
            request (ClientRequest): The client request to authenticate.

        Returns:
            UserAuthentication: The authentication result. Never `None`.

        Raises:
            ProcessingException: If the given client authentication is invalid.
        """
        _check_client_auth_types(request)
        assert request.authentication is not None
        user = self._validate_user_authentication_by(
            request.authentication.username,
            request.authentication.password
        )
        is_authenticated = user is not None
        if is_authenticated:
            self._set_authenticated_user(request, user)

        return UserAuthentication(user, is_authenticated)

    def _validate_user_authentication_by(
        self,
        username: str,
        password: str
    ) -> Optional[User]:
        user = self._ds.users().find_by_identifier(username)
        if self._user_record_has_password_set(user):
            assert user is not None
            if not StoredPasswordHash.is_stored_representation(
                str(user.password)
            ):
                self.constitute_password_authentication(user)
                self._ds.users().update(user)

            stored = StoredPasswordHash.from_compact_string(
                user.password # type: ignore
            )
            if PasswordValidation.validate_equality(password, stored):
                return user

        return None

    def _user_record_has_password_set(
        self,
        user_record: Optional[User]
    ) -> bool:
        return (
            user_record is not None
            and user_record.password is not None
            and str(user_record.password) != ""
            and UserState(user_record.state) in (
                UserState.INITIALIZED, UserState.ONBOARDING
            )
        )

    def _assign_password(self, user: User, hash_value: StoredPasswordHash):
        user.password = str(hash_value) # type: ignore

    def _set_authenticated_user(self, request: ClientRequest, user: User):
        request.user = BaseUser(
            user.identifier,
            user.name,
            state=UserState(str(user.state)),
        )
        assert request.authentication is not None
        request.authentication.password = "********"

    def _generate_password_salt(self) -> bytes:
        return EntropySource.instance().get_bytes(PASSWORD_SALT_LENGTH)
