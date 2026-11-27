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

from typing import cast

from raven.fathom.base.user import User, UserState
from raven.fathom.server.dao import DataAccess
from raven.fathom.server.models import UserPermission
from raven.fathom.server.core.user_management import UserPermissionKey
from raven.fathom.server.models import UserProjectRel, AuthDeployment
from raven.fathom.server.datastore.orm.field import OrmRecordId
from raven.fathom.server.models.user import UserRole
from raven.fathom.server.security import UserAuthenticator
from raven.fathom.server.security._hash import StoredPasswordHash
from raven.fathom.server.core.user_management import (
    UserManagementException,
    UserManager,
    UserStateException,
)

from tests.integration import DatabaseIntegrationTestCase


class TestUserManagement(DatabaseIntegrationTestCase):
    """Tests user management operations against the database."""

    def setUp(self):
        super().setUp()
        self.db = DataAccess.instance()
        self.mananger = UserManager(UserAuthenticator())

    def test_can_create_regular_user(self):
        user = User(
            identifier="test-user-2",
            state=UserState.ONBOARDING,
            name="Test User 2",
        )
        self.mananger.create_user(user)

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
        self.assertEqual(stored_user.role, UserRole.USER)

    def test_can_setup_onboarding_user(self):
        user = User(
            identifier="test-user-2",
            state=UserState.ONBOARDING,
            name="Test User 2",
        )
        self.mananger.create_user(user)
        user.password = "secret-password"
        self.mananger.sign_up_user(user)

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
        self.mananger.create_user(user)

        self.assertTrue(user.is_admin)
        self.assertEqual(user.state, UserState.ONBOARDING)
        stored_user = self.db.users().find_by_identifier("admin-user")
        assert stored_user is not None
        self.assertEqual(stored_user.role, UserRole.ADMINISTRATOR)

    def test_can_create_system_user_during_setup(self):
        self.db.users().delete_by_identifier("fathom")

        self.mananger.create_system_user("fathom", "secret-password")

        stored = self.db.users().find_by_identifier("fathom")
        assert stored is not None
        self.assertEqual(stored.identifier, "fathom")
        self.assertEqual(stored.name, "Fathom System User")
        self.assertEqual(stored.role, UserRole.SYSTEM)
        self.assertEqual(stored.state, UserState.ACTIVE)
        self.assertTrue(
            StoredPasswordHash.is_stored_representation(str(stored.password))
        )

    def test_cannot_create_second_system_user(self):
        with self.assertRaises(UserManagementException) as raised:
            self.mananger.create_system_user("fathom", "another-pass")

        self.assertIn("already been set up", str(raised.exception))

    def test_reset_user_sets_reset_state_and_stamps_shared_secret(self):
        self.mananger.reset_user("test-user-1")

        stored = self.db.users().find_by_identifier("test-user-1")
        assert stored is not None
        self.assertEqual(stored.state, UserState.RESET)
        self.assertTrue(
            StoredPasswordHash.is_stored_representation(str(stored.password))
        )

    def test_reset_user_enables_re_signup(self):
        self.mananger.reset_user("test-user-1")

        user = User(identifier="test-user-1", password="brand-new-password")
        self.mananger.sign_up_user(user)

        self.assertEqual(user.state, UserState.ACTIVE)
        stored = self.db.users().find_by_identifier("test-user-1")
        assert stored is not None
        self.assertEqual(stored.state, UserState.ACTIVE)

    def test_rotate_shared_secret_updates_settings(self):
        new_secret = "rotated-secret-value"

        self.mananger.rotate_shared_secret(new_secret)

        settings = self.db.settings().find_server_settings()
        self.assertEqual(settings.shared_secret, new_secret)

    def test_list_users_returns_admin_state(self):
        user = User(
            identifier="test-user-2",
            state=UserState.ONBOARDING,
        )
        self.mananger.create_user(user)

        users = self.mananger.list_users()

        identifiers = [u.identifier for u in users]
        self.assertIn("admin", identifiers)
        self.assertIn("test-user-1", identifiers)
        self.assertIn("test-user-2", identifiers)
        admin = next(u for u in users if u.identifier == "admin")
        user1 = next(u for u in users if u.identifier == "test-user-1")
        user2 = next(u for u in users if u.identifier == "test-user-2")
        self.assertTrue(admin.is_admin)
        self.assertEqual(admin.state, UserState.ACTIVE)
        self.assertFalse(user1.is_admin)
        self.assertEqual(user1.state, UserState.ACTIVE)
        self.assertFalse(user2.is_admin)
        self.assertEqual(user2.state, UserState.ONBOARDING)

    def test_delete_user_removes_associated_records(self):
        user_record = self.db.users().find_by_identifier("test-user-1")
        assert user_record is not None
        user_record_id = cast(OrmRecordId, user_record.datastore_id).value
        self.mananger.delete_user(User(identifier=user_record.identifier))

        deleted_user_record = self.db.users().find_by_identifier("test-user-1")
        self.assertIsNone(deleted_user_record)
        # pylint: disable=protected-access
        self.assertEqual(UserPermission.select().where(
            UserPermission._user == user_record_id
        ).count(), 0)
        self.assertEqual(UserProjectRel.select().where(
            UserProjectRel.user == user_record_id
        ).count(), 0)
        # pylint: disable=no-value-for-parameter
        self.assertEqual(AuthDeployment.select().count(), 0) # type: ignore

    def test_can_set_user_permission(self):
        user_record = self.db.users().find_by_identifier("test-user-1")
        assert user_record is not None
        permission = self.db.users().find_permission(user_record)
        self.assertTrue(permission.allow_overwrite)

        self.mananger.set_user_permission(
            User(identifier="test-user-1"),
            UserPermissionKey.ALLOW_OVERWRITE,
            "OFF",
        )

        persisted = self.db.users().find_permission(user_record)
        self.assertFalse(persisted.allow_overwrite)

    def test_cannot_set_system_user_permission(self):
        with self.assertRaises(UserStateException) as raised:
            self.mananger.set_user_permission(
                User(identifier="fathom"),
                UserPermissionKey.ALLOW_OVERWRITE,
                "OFF",
            )

        self.assertIn(
            "system user cannot be changed",
            str(raised.exception),
        )
        system_user = self.db.users().find_by_identifier("fathom")
        assert system_user is not None
        permission = self.db.users().find_permission(system_user)
        self.assertTrue(permission.allow_overwrite)

    def test_delete_rejects_system_user(self):
        with self.assertRaises(UserStateException) as raised:
            self.mananger.delete_user(
                User(identifier="fathom")
            )

        self.assertIn(
            "The system user cannot be deleted",
            str(raised.exception)
        )


if __name__ == "__main__":
    DatabaseIntegrationTestCase.run_tests()
