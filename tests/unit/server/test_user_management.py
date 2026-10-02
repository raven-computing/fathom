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
"""Unit tests for server-side user management logic."""

from raven.fathom.base import User, UserState
from raven.fathom.server.models import User as UserModel
from raven.fathom.server.models import UserRole
from raven.fathom.server.models import Settings
from raven.fathom.server.security import UserAuthenticator
from raven.fathom.server.user_management import UserManager

from tests.unit import TestCase
from tests.unit.mocks import Mock
from tests.unit.server.mocks import DataAccessMock


class TestUserManager(TestCase):
    """Unit tests for `UserManager`."""

    def setUp(self):
        super().setUp()
        self.ds = DataAccessMock.instance()
        DataAccessMock.reset()
        self.authenticator = Mock(spec_set=UserAuthenticator)
        self.manager = UserManager(self.authenticator)
        self.settings = Settings(
            organisation_name = "Test Org",
            shared_secret = "shared-secret",
            active=True,
        )
        self.ds.settings().find_server_settings.return_value = self.settings

    def test_create_system_user_rejects_empty_password(self):
        user = User(identifier="ignored", password="")

        with self.assertRaises(ValueError) as raised:
            self.manager.create_system_user(user)

        self.assertIn("password must not be empty", str(raised.exception))

    def test_create_user_requires_shared_secret(self):
        self.ds.users().find_by_identifier.return_value = None
        self.settings.shared_secret = ""
        user = User(identifier="new-user", state=UserState.ONBOARDING)

        with self.assertRaises(ValueError) as raised:
            self.manager.create_user(user)

        self.assertIn("No shared secret set", str(raised.exception))

    def test_sign_up_user_updates_record_and_redacts_password(self):
        user_record = UserModel(
            identifier="new-user",
            name="New User",
            password="shared-secret",
            role=UserRole.USER,
            state=UserState.ONBOARDING,
        )
        self.ds.users().find_by_identifier.return_value = user_record
        user = User(identifier="new-user", password="new-password")

        self.manager.sign_up_user(user)

        self.assertEqual(user.identifier, "new-user")
        self.assertEqual(user.name, "New User")
        self.assertEqual(user.password, "")
        self.assertEqual(user.state, UserState.ACTIVE)
        self.assertFalse(user.is_admin)
        self.assertEqual(user_record.password, "new-password")
        self.assertEqual(user_record.state, UserState.ACTIVE)
        method = self.authenticator.constitute_password_authentication
        method.assert_called_once_with(user_record)
        self.ds.users().update.assert_called_once_with(user_record)

    def test_list_users_excludes_system_user(self):
        self.ds.users().read_all.return_value = [
            UserModel(
                identifier="fathom",
                name="Fathom System User",
                password="secret",
                role=UserRole.SYSTEM,
                state=UserState.ACTIVE,
            ),
            UserModel(
                identifier="alpha",
                name="Alpha User",
                password="secret",
                role=UserRole.USER,
                state=UserState.ACTIVE,
            ),
        ]

        users = self.manager.list_users()

        self.assertEqual(["alpha"], [user.identifier for user in users])
        self.assertFalse(users[0].is_admin)
        self.assertEqual(users[0].state, UserState.ACTIVE)


if __name__ == "__main__":
    TestCase.run_tests()
