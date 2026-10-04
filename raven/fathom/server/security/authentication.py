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
from raven.fathom.server.models import UserRole
from raven.fathom.server.logging import Logger
from raven.fathom.server.security._hash import PasswordHasher
from raven.fathom.server.security._hash import StoredPasswordHash
from raven.fathom.server.security._hash import PasswordValidation


LOG = Logger.get()

PASSWORD_ENCODING: Final = "UTF-8"

PASSWORD_SALT_LENGTH: Final = 16


def _check_auth_types(auth: ClientAuthentication):
    """Safety check for username-password-combination in a made request."""
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


def _check_client_auth_types(request: ClientRequest):
    """Safety check for a made client request."""
    TypeCheck.require_arg(request, ClientRequest)
    auth = request.authentication
    if auth is None:
        raise ProcessingException("Client has no authentication set")

    _check_auth_types(auth)


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
    """Handles user authentication.

    Attributes:
        hasher (PasswordHasher): The `PasswordHasher` object used by
            the authenticator.
    """

    def __init__(self):
        """Initializes a new `UserAuthenticator` instance."""
        self.hasher = PasswordHasher.get_default()
        self._ds = DataAccess.instance()
        self._dummy_hash = self._build_dummy_password_hash()

    def constitute_password_authentication(self, user: User):
        """Sets up authentication via a password for the given user.

        Args:
            user (User): The user record with a valid identifier and password.

        Raises:
            ProcessingException: If the user record does not have a valid
                identifier or password set.
        """
        _check_user_record_types(user)
        salt = self._generate_password_salt()
        password_hash = self.hasher.digest(
            user.password.encode(PASSWORD_ENCODING), # type: ignore
            salt
        )
        self._assign_password(
            user,
            StoredPasswordHash(
                self.hasher.specification(),
                salt.hex(),
                password_hash.hex()
            )
        )

    def authenticate_signup_request(
        self,
        authentication: ClientAuthentication
    ) -> UserAuthentication:
        """Authenticates the given request to sign up a new user.

        Args:
            authentication (ClientAuthentication): The client authentication
                information used in the signup request.

        Returns:
            UserAuthentication: The authentication result. Never `None`.

        Raises:
            ProcessingException: If the given authentication is invalid.
        """
        _check_auth_types(authentication)
        user = self._ds.users().find_by_identifier(authentication.username)
        is_authenticated = False
        if self._onboarding_user_record_has_password_set(user):
            assert user is not None
            user = self._validate_user_authentication_by(
                user,
                authentication.password
            )
            is_authenticated = user is not None
        else:
            self._spin_authentication_process(authentication.password)

        return UserAuthentication(user, is_authenticated)

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
        user = self._ds.users().find_by_identifier(
            request.authentication.username
        )
        is_authenticated = False
        if self._active_non_system_user_record_has_password_set(user):
            assert user is not None
            user = self._validate_user_authentication_by(
                user,
                request.authentication.password
            )
            is_authenticated = user is not None
        else:
            self._spin_authentication_process(request.authentication.password)

        if is_authenticated:
            assert user is not None
            self._set_authenticated_client(request, user)

        return UserAuthentication(user, is_authenticated)

    def authenticate_system_user(
        self,
        authentication: ClientAuthentication
    ) -> UserAuthentication:
        """Authenticates the local Fathom system user for server CLI usage."""
        _check_auth_types(authentication)
        user = self._ds.users().find_by_identifier(authentication.username)
        is_authenticated = False
        if self._active_system_user_record_has_password_set(user):
            assert user is not None
            user = self._validate_user_authentication_by(
                user,
                authentication.password
            )
            is_authenticated = user is not None
        else:
            self._spin_authentication_process(authentication.password)

        return UserAuthentication(user, is_authenticated)

    def _validate_user_authentication_by(
        self,
        user: User,
        password: str
    ) -> Optional[User]:
        assert user is not None
        if not StoredPasswordHash.is_stored_representation(str(user.password)):
            LOG.i(
                "Hashing found plain-text password for user %s",
                user.identifier
            )
            self._store_hashed_password_for(user)

        stored = StoredPasswordHash.from_compact_string(
            user.password # type: ignore
        )

        if PasswordValidation.validate_equality(password, stored):
            if stored.rounds != self.hasher.rounds:
                LOG.i(
                    "Rehashing password for user %s due to changed "
                    "hash rounds",
                    user.identifier
                )
                user.password = password
                self._store_hashed_password_for(user)

            return user

        return None

    def _active_user_record_has_password_set(
        self,
        user_record: Optional[User]
    ) -> bool:
        return (
            user_record is not None
            and user_record.password is not None
            and str(user_record.password) != ""
            and UserState(user_record.state) == UserState.ACTIVE
        )

    def _active_non_system_user_record_has_password_set(
        self,
        user_record: Optional[User]
    ) -> bool:
        return (
            self._active_user_record_has_password_set(user_record)
            and user_record is not None
            and UserRole(str(user_record.role)) != UserRole.SYSTEM
        )

    def _active_system_user_record_has_password_set(
        self,
        user_record: Optional[User]
    ) -> bool:
        return (
            self._active_user_record_has_password_set(user_record)
            and user_record is not None
            and UserRole(str(user_record.role)) == UserRole.SYSTEM
        )

    def _onboarding_user_record_has_password_set(
        self,
        user_record: Optional[User]
    ) -> bool:
        return (
            user_record is not None
            and user_record.password is not None
            and str(user_record.password) != ""
            and UserState(user_record.state) == UserState.ONBOARDING
        )

    def _store_hashed_password_for(self, user: User):
        self.constitute_password_authentication(user)
        self._ds.users().update(user)

    def _assign_password(self, user: User, hash_value: StoredPasswordHash):
        user.password = str(hash_value) # type: ignore

    def _set_authenticated_client(self, request: ClientRequest, user: User):
        request.authenticated_user = BaseUser(
            user.identifier,
            user.name,
            is_admin=UserRole(user.role).has_administrative_privileges(),
            state=UserState(str(user.state)),
        )
        assert request.authentication is not None
        request.authentication.password = "********"

    def _generate_password_salt(self) -> bytes:
        return EntropySource.instance().get_bytes(PASSWORD_SALT_LENGTH)

    def _build_dummy_password_hash(self) -> StoredPasswordHash:
        dummy_password = "fathom-authentication-dummy-password"
        dummy_password_salt = b"\x00" * PASSWORD_SALT_LENGTH
        dummy_hash = self.hasher.digest(
            dummy_password.encode(PASSWORD_ENCODING),
            dummy_password_salt
        )
        return StoredPasswordHash(
            self.hasher.specification(),
            dummy_password_salt.hex(),
            dummy_hash.hex()
        )

    def _spin_authentication_process(self, password: str):
        """Performs a password validation against a dummy password hash.

        This is used to simulate password verification for a dummy user.
        It helps prevent timing attacks by ensuring that the authentication
        process takes an approximately consistent amount of time, even for
        non-existent users.
        """
        PasswordValidation.validate_equality(password, self._dummy_hash)
