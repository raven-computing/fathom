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

from raven.fathom.base.project import Project
from raven.fathom.base.user import User, UserState
from raven.fathom.server.dao import DataAccess
from raven.fathom.server.models import UserPermission
from raven.fathom.server.models import UserProjectRel, AuthDeployment
from raven.fathom.server.models.user import UserRole
from raven.fathom.server.security import UserAuthenticator
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
        UserManager(UserAuthenticator()).create_user(user)

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
        permission = self.db.users().find_permission(stored_user)
        self.assertFalse(permission.is_admin)

    def test_can_setup_onboarding_user(self):
        user = User(
            identifier="test-user-2",
            state=UserState.ONBOARDING,
            name="Test User 2",
        )
        UserManager(UserAuthenticator()).create_user(user)
        user.password = "secret-password"
        UserManager(UserAuthenticator()).sign_up_user(user)

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
        UserManager(UserAuthenticator()).create_user(user)

        self.assertTrue(user.is_admin)
        self.assertEqual(user.state, UserState.ONBOARDING)
        stored_user = self.db.users().find_by_identifier("admin-user")
        assert stored_user is not None
        self.assertEqual(stored_user.role, UserRole.ADMINISTRATOR)
        permission = self.db.users().find_permission(stored_user)
        self.assertTrue(permission.is_admin)

    def test_can_create_system_user_during_setup(self):
        self.db.users().delete_by_identifier("fathom")
        user = User(
            identifier="ignored",
            name="Ignored",
            password="secret-password"
        )

        UserManager(UserAuthenticator()).create_system_user(user)

        stored_user = self.db.users().find_by_identifier("fathom")
        assert stored_user is not None
        self.assertEqual(stored_user.identifier, "fathom")
        self.assertEqual(stored_user.name, "Fathom System User")
        self.assertEqual(stored_user.role, UserRole.SYSTEM)
        self.assertEqual(stored_user.state, UserState.ACTIVE)

    def test_cannot_create_second_system_user(self):
        with self.assertRaises(ValueError) as raised:
            UserManager(UserAuthenticator()).create_system_user(
                User(password="secret-password", identifier="ignored")
            )

        self.assertIn("already been set up", str(raised.exception))

    def test_list_users_returns_admin_state(self):
        user = User(
            identifier="test-user-2",
            state=UserState.ONBOARDING,
        )
        UserManager(UserAuthenticator()).create_user(user)

        users = UserManager(UserAuthenticator()).list_users()

        self.assertEqual(
            [user.identifier for user in users],
            ["fathom", "test-user-1", "test-user-2"]
        )
        self.assertTrue(users[0].is_admin)
        self.assertFalse(users[1].is_admin)
        self.assertFalse(users[2].is_admin)
        self.assertEqual(users[0].state, UserState.ACTIVE)
        self.assertEqual(users[1].state, UserState.ACTIVE)
        self.assertEqual(users[2].state, UserState.ONBOARDING)

    def test_delete_user_removes_associated_records(self):
        user = User(
            identifier="test-user-2",
            name="Test User 2",
            state=UserState.ONBOARDING,
        )
        UserManager(UserAuthenticator()).create_user(user)
        UserManager(UserAuthenticator()).assign_user_to_project(
            User(identifier="test-user-2"),
            Project(identifier="test-project-1"),
        )
        user_record_id = self.db.users().find_by_identifier(
            "test-user-2"
        ).id # type: ignore
        UserManager(UserAuthenticator()).delete_user(user)

        deleted_user_record = self.db.users().find_by_identifier("test-user-2")
        self.assertIsNone(deleted_user_record)
        self.assertEqual(UserPermission.select().where(
            UserPermission.user == user_record_id
        ).count(), 0)
        self.assertEqual(UserProjectRel.select().where(
            UserProjectRel.user == user_record_id
        ).count(), 0)
        # pylint: disable=no-value-for-parameter
        self.assertEqual(AuthDeployment.select().count(), 1) # type: ignore

    def test_delete_rejects_system_user(self):
        with self.assertRaises(ValueError) as raised:
            UserManager(UserAuthenticator()).delete_user(
                User(identifier="fathom")
            )

        self.assertIn("system user cannot be changed", str(raised.exception))

    def test_can_assign_user_to_project(self):
        UserManager(UserAuthenticator()).assign_user_to_project(
            User(identifier="fathom"),
            Project(identifier="test-project-2"),
        )

        user = self.db.users().find_by_identifier("fathom")
        assert user is not None
        assigned_projects = self.db.projects().find_all_assigned_to_user(user)
        self.assertEqual(
            sorted(project.identifier for project in assigned_projects),
            ["test-project-2"],
        )

    def test_can_unassign_user_from_project(self):
        UserManager(UserAuthenticator()).assign_user_to_project(
            User(identifier="fathom"),
            Project(identifier="test-project-1"),
        )
        UserManager(UserAuthenticator()).unassign_user_from_project(
            User(identifier="fathom"),
            Project(identifier="test-project-1"),
        )

        user = self.db.users().find_by_identifier("fathom")
        assert user is not None
        assigned_projects = self.db.projects().find_all_assigned_to_user(user)
        self.assertEqual(assigned_projects, [])


if __name__ == "__main__":
    DatabaseIntegrationTestCase.run_tests()
