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
"""Integration tests for server-side user management."""

from raven.fathom.base.user import User, UserState
from raven.fathom.server.dao import DataAccess
from raven.fathom.server.models import UserPermission
from raven.fathom.server.models import UserProjectRel, AuthDeployment
from raven.fathom.server.security._hash import StoredPasswordHash
from raven.fathom.server.user_management import UserManager

from tests.integration import DatabaseIntegrationTestCase


class TestUserManagement(DatabaseIntegrationTestCase):
    """Tests user management operations against the database."""

    def setUp(self):
        super().setUp()
        self.db = DataAccess.instance()

    def test_can_create_regular_user(self):
        user = User(
            identifier="test-user-2",
            state=UserState.ONBOARDING,
            name="Test User 2",
        )
        UserManager().create_user(user)

        self.assertEqual(user.identifier, "test-user-2")
        self.assertEqual(user.name, "Test User 2")
        self.assertFalse(user.is_admin)
        self.assertEqual(user.state, UserState.ONBOARDING)
        stored_user = self.db.users().find_by_identifier("test-user-2")
        self.assertIsNotNone(stored_user)
        assert stored_user is not None
        self.assertTrue(
            StoredPasswordHash.is_stored_representation(
                str(stored_user.password)
            )
        )
        self.assertEqual(stored_user.state, UserState.ONBOARDING)
        permission = self.db.users().find_permission(stored_user)
        self.assertFalse(permission.is_admin)

    def test_can_setup_onboarding_user(self):
        user = User(
            identifier="test-user-2",
            state=UserState.ONBOARDING,
            name="Test User 2",
        )
        UserManager().create_user(user)
        user.password = "secret-password"
        UserManager().setup_user(user)

        self.assertEqual(user.identifier, "test-user-2")
        self.assertEqual(user.state, UserState.ACTIVE)
        stored_user = self.db.users().find_by_identifier("test-user-2")
        assert stored_user is not None
        self.assertTrue(
            StoredPasswordHash.is_stored_representation(
                str(stored_user.password)
            )
        )
        self.assertEqual(stored_user.state, UserState.ACTIVE)

    def test_can_create_admin_user(self):
        user = User(
            identifier="admin-user",
            state=UserState.ONBOARDING,
            is_admin=True,
        )
        UserManager().create_user(user)

        self.assertTrue(user.is_admin)
        self.assertEqual(user.state, UserState.ONBOARDING)
        stored_user = self.db.users().find_by_identifier("admin-user")
        assert stored_user is not None
        permission = self.db.users().find_permission(stored_user)
        self.assertTrue(permission.is_admin)

    def test_list_users_returns_admin_state(self):
        user = User(
            identifier="test-user-2",
            state=UserState.ONBOARDING,
        )
        UserManager().create_user(user)

        users = UserManager().list_users()

        self.assertEqual(
            [user.identifier for user in users],
            ["test-user-1", "test-user-2"]
        )
        self.assertTrue(users[0].is_admin)
        self.assertFalse(users[1].is_admin)
        self.assertEqual(users[0].state, UserState.ACTIVE)
        self.assertEqual(users[1].state, UserState.ONBOARDING)

    def test_delete_user_removes_associated_records(self):
        user = User(identifier="test-user-1")
        UserManager().delete_user(user)

        self.assertIsNone(self.db.users().find_by_identifier("test-user-1"))
        # pylint: disable=no-value-for-parameter
        self.assertEqual(UserPermission.select().count(), 0)
        self.assertEqual(UserProjectRel.select().count(), 0)
        self.assertEqual(AuthDeployment.select().count(), 0)


if __name__ == "__main__":
    DatabaseIntegrationTestCase.run_tests()
