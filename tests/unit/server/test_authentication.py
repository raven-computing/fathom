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
"""Unit tests for authentication module."""

from raven.fathom.base import ClientRequest, ClientAuthentication
from raven.fathom.base import Interaction, ProcessingException
from raven.fathom.base.user import UserState
from raven.fathom.base.testing import EntropySourceMock
from raven.fathom.server.security import UserAuthenticator, UserAuthentication
from raven.fathom.server.security._hash import StoredPasswordHash
from raven.fathom.server.models import User
from raven.fathom.server.models import UserRole

from tests.unit import TestCase
from tests.unit.server.mocks import DataAccessMock


class TestUserAuthentication(TestCase):
    """Unit tests for the `UserAuthentication` class."""

    def setUp(self):
        super().setUp()
        self.authenticator = UserAuthenticator()
        self.hash_rounds = 2048
        self.authenticator.hasher.rounds = self.hash_rounds
        self.user_signup = User(
            identifier="test-user-1",
            name="The Test User 1",
            password="test-cleartext-password-1",
            state=UserState.ACTIVE,
        )
        salt_byte = EntropySourceMock.instance().next_byte.hex()
        self.known_user_password_salt: str = salt_byte * 16
        self.known_user_password_hash: str = (
            f"pbkdf2-hmac-sha512-{self.hash_rounds}"
            f":{self.known_user_password_salt}:"
            "a6434b3447272736cb57107aa22818637765992c39061f884da4f18d71042431"
            "d2f84a97e35f832a859743b161b57992a917c8de5685dcdfc1d759a1d35136d1"
        )
        self.user_stored = User(
            identifier=self.user_signup.identifier,
            name=self.user_signup.name,
            password=self.known_user_password_hash,
            role=UserRole.USER,
            state=self.user_signup.state,
        )
        self.client_request = ClientRequest(
            action=Interaction.REQUEST_DEPLOYMENT
        )
        self.client_request.authentication = ClientAuthentication(
            username=str(self.user_signup.identifier),
            password=str(self.user_signup.password),
        )
        self.dao = DataAccessMock()
        self.dao.reset()

    def test_can_constitute_password_authentication_for_user_record(self):
        user = self.user_signup
        self.authenticator.constitute_password_authentication(user)
        self.assertEqual(user.identifier, "test-user-1")
        self.assertEqual(user.name, "The Test User 1")
        self.assertEqual(
            user.password,
            self.known_user_password_hash,
            "Setting up password authentication for user should store "
            "hashed password in user record."
        )

    def test_correct_username_password_combination_authenticates_user(self):
        self.dao.users().find_by_identifier.return_value = self.user_stored
        auth = self.authenticator.authenticate_client(self.client_request)
        self.assertIsInstance(auth, UserAuthentication)
        self.assertTrue(auth.is_authenticated())
        self.assertIsInstance(auth.user_record, User)
        self.assertIs(auth.user_record, self.user_stored)

    def test_wrong_username_in_client_request_denies_user_authentication(self):
        self.user_stored.identifier = "an-unknown-user" # type: ignore
        self.dao.users().find_by_identifier.return_value = None
        auth = self.authenticator.authenticate_client(self.client_request)
        self.assertIsInstance(auth, UserAuthentication)
        self.assertFalse(auth.is_authenticated())
        self.assertIsNone(auth.user_record)

    def test_wrong_password_in_client_request_denies_user_authentication(self):
        self.dao.users().find_by_identifier.return_value = self.user_stored
        # Test with minimal change to correct password
        wrong_password = str(self.user_signup.password) + "A"
        assert self.client_request.authentication is not None
        self.client_request.authentication.password = wrong_password
        auth = self.authenticator.authenticate_client(self.client_request)
        self.assertIsInstance(auth, UserAuthentication)
        self.assertFalse(auth.is_authenticated())
        self.assertIsNone(auth.user_record)

    def test_onboarding_user_is_not_authenticated_with_matching_password(self):
        self.user_stored.state = UserState.ONBOARDING # type: ignore
        self.dao.users().find_by_identifier.return_value = self.user_stored
        auth = self.authenticator.authenticate_client(self.client_request)
        self.assertIsInstance(auth, UserAuthentication)
        self.assertFalse(auth.is_authenticated())
        self.assertIsNotNone(auth.user_record)

    def test_cleartext_password_is_hashed_on_successful_authentication(self):
        self.dao.users().find_by_identifier.return_value = self.user_signup
        auth = self.authenticator.authenticate_client(self.client_request)
        self.assertTrue(auth.is_authenticated())
        self.assertEqual(
            self.user_signup.password,
            self.known_user_password_hash,
            "Password should be hashed after successful authentication"
        )

    def test_password_is_rehashed_on_successful_auth_when_rounds_change(self):
        self.dao.users().find_by_identifier.return_value = self.user_stored
        self.authenticator.hasher.rounds += 1

        auth = self.authenticator.authenticate_client(self.client_request)

        self.assertTrue(auth.is_authenticated())
        self.dao.users().update.assert_called_once_with(self.user_stored)
        rehashed = StoredPasswordHash.from_compact_string(
            str(self.user_stored.password)
        )
        self.assertEqual(rehashed.rounds, self.authenticator.hasher.rounds)
        self.assertNotEqual(rehashed.hash_value, self.known_user_password_hash)
        self.assertEqual(rehashed.salt, self.known_user_password_salt)

    def test_can_authenticate_with_old_password_when_stored_is_rehashed(self):
        self.dao.users().find_by_identifier.return_value = self.user_stored
        self.authenticator.hasher.rounds += 1
        # Cause password rehash
        auth = self.authenticator.authenticate_client(self.client_request)
        self.assertTrue(auth.is_authenticated())

        assert self.client_request.authentication is not None
        assert self.user_signup.password is not None
        self.client_request.authentication.password = self.user_signup.password
        auth = self.authenticator.authenticate_client(self.client_request)

        self.assertTrue(auth.is_authenticated())

    def test_password_is_not_rehashed_on_unsuccessful_auth(self):
        self.dao.users().find_by_identifier.return_value = self.user_stored
        self.authenticator.hasher.rounds += 1
        assert self.client_request.authentication is not None
        self.client_request.authentication.password = "wrong-password"

        auth = self.authenticator.authenticate_client(self.client_request)

        self.assertFalse(auth.is_authenticated())
        self.dao.users().update.assert_not_called()
        hashed = StoredPasswordHash.from_compact_string(
            str(self.user_stored.password)
        )
        self.assertEqual(self.known_user_password_hash, str(hashed))

    def test_client_auth_is_exchanged_to_authenticated_user_on_success(self):
        self.dao.users().find_by_identifier.return_value = self.user_signup
        auth = self.authenticator.authenticate_client(self.client_request)
        self.assertTrue(auth.is_authenticated())
        assert self.client_request.authentication is not None
        self.assertEqual(
            self.client_request.authentication.username,
            self.user_signup.identifier,
        )
        self.assertEqual(
            self.client_request.authentication.password,
            "********",
            "Authentication password should be redacted after "
            "successful authentication"
        )
        assert self.client_request.authenticated_user is not None
        self.assertEqual(
            self.client_request.authenticated_user.identifier,
            self.user_signup.identifier
        )
        self.assertEqual(
            self.client_request.authenticated_user.name,
            self.user_signup.name
        )

    def test_client_authentication_is_not_exchanged_on_failed_auth(self):
        self.dao.users().find_by_identifier.return_value = None
        auth = self.authenticator.authenticate_client(self.client_request)
        self.assertFalse(auth.is_authenticated())
        assert self.client_request.authentication is not None
        self.assertEqual(
            self.client_request.authentication.username,
            self.user_signup.identifier,
        )
        self.assertEqual(
            self.client_request.authentication.password,
            self.user_signup.password,
        )

    def test_system_user_is_rejected_for_remote_client_authentication(self):
        self.user_stored.role = UserRole.SYSTEM
        self.dao.users().find_by_identifier.return_value = self.user_stored

        auth = self.authenticator.authenticate_client(self.client_request)

        self.assertFalse(auth.is_authenticated())
        self.assertIsNotNone(auth.user_record)

    def test_system_user_can_authenticate_for_local_server_commands(self):
        self.user_stored.role = UserRole.SYSTEM
        authentication = ClientAuthentication(
            username=str(self.user_signup.identifier),
            password=str(self.user_signup.password),
        )
        self.dao.users().find_by_identifier.return_value = self.user_stored

        auth = self.authenticator.authenticate_system_user(authentication)

        self.assertTrue(auth.is_authenticated())
        self.assertIs(auth.user_record, self.user_stored)

    def test_authenticate_client_without_auth_raises_processing_ex(self):
        self.client_request.authentication = None
        with self.assertRaises(ProcessingException) as raised:
            self.authenticator.authenticate_client(self.client_request)

        self.assertEqual(
            "Client has no authentication set",
            str(raised.exception)
        )

    def test_authenticate_client_empty_username_raises_processing_ex(self):
        assert self.client_request.authentication is not None
        self.client_request.authentication.username = ""
        with self.assertRaises(ProcessingException) as raised:
            self.authenticator.authenticate_client(self.client_request)

        self.assertIn("username must not be empty", str(raised.exception))

    def test_authenticate_client_with_empty_password_raises_ex(self):
        assert self.client_request.authentication is not None
        self.client_request.authentication.password = ""
        with self.assertRaises(ProcessingException) as raised:
            self.authenticator.authenticate_client(self.client_request)

        self.assertIn("password must not be empty", str(raised.exception))

    def test_constitute_password_with_empty_identifier_raises_ex(self):
        user = User(identifier="", name="User", password="password")
        with self.assertRaises(ProcessingException) as raised:
            self.authenticator.constitute_password_authentication(user)

        self.assertIn(
            "User identifier must not be empty",
            str(raised.exception)
        )

    def test_constitute_password_with_empty_password_raises_ex(self):
        user = User(identifier="user", name="User", password="")
        with self.assertRaises(ProcessingException) as raised:
            self.authenticator.constitute_password_authentication(user)

        self.assertIn("User password must not be empty", str(raised.exception))


if __name__ == "__main__":
    TestCase.run_tests()
