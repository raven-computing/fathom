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

from typing import cast

from raven.fathom.base import Project, User, UserState
from raven.fathom.server.models import User as UserModel
from raven.fathom.server.models import UserRole
from raven.fathom.server.models import Settings
from raven.fathom.server.models import UserPermission
from raven.fathom.server.models import SYSTEM_USER_IDENTIFIER
from raven.fathom.server.models import SYSTEM_USER_NAME
from raven.fathom.server.dao import IncoherentDatastoreStateException
from raven.fathom.server.domain import (
    ProjectManagementException,
    ProjectManager,
)
from raven.fathom.server.security import UserAuthenticator
from raven.fathom.server.core.user_management import (
    UserManagementException,
    UserAlreadyExistsException,
    UserNotFoundException,
    UserStateException,
    InvalidUserRequestException,
    UserManager,
    UserPermissionKey,
)

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

    def test_is_setup_complete_returns_false_without_settings(self):
        self.ds.settings().find_server_settings.side_effect = (
            IncoherentDatastoreStateException("No settings found")
        )

        self.assertFalse(self.manager.is_setup_complete())

    def test_is_setup_complete_returns_false_without_active_admin(self):
        self.ds.users().read_all.return_value = [
            UserModel(
                identifier=SYSTEM_USER_IDENTIFIER,
                name=SYSTEM_USER_NAME,
                role=UserRole.SYSTEM,
                state=UserState.ACTIVE,
            ),
            UserModel(
                identifier="user1",
                name="User 1",
                role=UserRole.USER,
                state=UserState.ACTIVE,
            ),
        ]

        self.assertFalse(self.manager.is_setup_complete())

    def test_is_setup_complete_returns_true_with_active_admin(self):
        self.ds.users().read_all.return_value = [
            UserModel(
                identifier=SYSTEM_USER_IDENTIFIER,
                name=SYSTEM_USER_NAME,
                role=UserRole.SYSTEM,
                state=UserState.ACTIVE,
            ),
            UserModel(
                identifier="admin1",
                name="Admin",
                role=UserRole.ADMINISTRATOR,
                state=UserState.ACTIVE,
            ),
        ]

        self.assertTrue(self.manager.is_setup_complete())

    def test_is_setup_complete_accepts_reset_admin_as_valid(self):
        self.ds.users().read_all.return_value = [
            UserModel(
                identifier=SYSTEM_USER_IDENTIFIER,
                name=SYSTEM_USER_NAME,
                role=UserRole.SYSTEM,
                state=UserState.ACTIVE,
            ),
            UserModel(
                identifier="admin1",
                name="Admin",
                role=UserRole.ADMINISTRATOR,
                state=UserState.RESET,
            ),
        ]

        self.assertTrue(self.manager.is_setup_complete())

    def test_is_setup_complete_requires_system_user(self):
        self.ds.users().read_all.return_value = [
            UserModel(
                identifier="admin1",
                name="Admin",
                role=UserRole.ADMINISTRATOR,
                state=UserState.ACTIVE,
            ),
        ]

        self.assertFalse(self.manager.is_setup_complete())

    def test_is_setup_complete_returns_false_for_onboarding_admin_only(self):
        self.ds.users().read_all.return_value = [
            UserModel(
                identifier=SYSTEM_USER_IDENTIFIER,
                name=SYSTEM_USER_NAME,
                role=UserRole.SYSTEM,
                state=UserState.ACTIVE,
            ),
            UserModel(
                identifier="admin1",
                name="Admin",
                role=UserRole.ADMINISTRATOR,
                state=UserState.ONBOARDING,
            ),
        ]

        self.assertFalse(self.manager.is_setup_complete())

    def test_create_initial_admin_creates_active_administrator(self):
        self.ds.users().find_by_identifier.return_value = None

        self.manager.create_initial_admin("admin1", "secret")

        const_pass_auth = (
            self.authenticator.constitute_password_authentication
        )
        const_pass_auth.assert_called_once()
        self.ds.users().create_new_user.assert_called_once()
        created_record = (
            self.ds.users().create_new_user.call_args[0][0]
        )
        self.assertEqual(created_record.identifier, "admin1")
        self.assertEqual(created_record.role, UserRole.ADMINISTRATOR)
        self.assertEqual(created_record.state, UserState.ACTIVE)

    def test_create_initial_admin_rejects_empty_identifier(self):
        with self.assertRaises(InvalidUserRequestException) as raised:
            self.manager.create_initial_admin("", "secret")

        self.assertIn("identifier must not be empty", str(raised.exception))
        self.ds.users().create_new_user.assert_not_called()

    def test_create_initial_admin_rejects_empty_password(self):
        with self.assertRaises(InvalidUserRequestException) as raised:
            self.manager.create_initial_admin("admin1", "")

        self.assertIn("password must not be empty", str(raised.exception))
        self.ds.users().create_new_user.assert_not_called()

    def test_create_initial_admin_rejects_duplicate_identifier(self):
        self.ds.users().find_by_identifier.return_value = UserModel(
            identifier="admin1", name="Admin"
        )

        with self.assertRaises(UserAlreadyExistsException):
            self.manager.create_initial_admin("admin1", "secret")

        self.ds.users().create_new_user.assert_not_called()

    def test_create_system_user_creates_active_system_user(self):
        self.ds.users().read_all.return_value = []

        self.manager.create_system_user(SYSTEM_USER_IDENTIFIER, "syspass")

        self.ds.users().create_new_user.assert_called_once()
        created = self.ds.users().create_new_user.call_args[0][0]
        self.assertEqual(created.identifier, SYSTEM_USER_IDENTIFIER)
        self.assertEqual(created.role, UserRole.SYSTEM)
        self.assertEqual(created.state, UserState.ACTIVE)

    def test_create_system_user_rejects_duplicate(self):
        self.ds.users().read_all.return_value = [
            UserModel(
                identifier=SYSTEM_USER_IDENTIFIER,
                name=SYSTEM_USER_NAME,
                role=UserRole.SYSTEM,
                state=UserState.ACTIVE,
            )
        ]

        with self.assertRaises(UserManagementException) as raised:
            self.manager.create_system_user(SYSTEM_USER_IDENTIFIER, "syspass")

        self.assertIn("already been set up", str(raised.exception))
        self.ds.users().create_new_user.assert_not_called()

    def test_reset_user_stamps_shared_secret_and_sets_reset_state(self):
        user_record = UserModel(
            identifier="user1",
            name="User 1",
            role=UserRole.USER,
            state=UserState.ACTIVE,
        )
        self.ds.users().find_by_identifier.return_value = user_record

        self.manager.reset_user("user1")

        self.assertEqual(user_record.state, UserState.RESET)
        auth_method = (
            self.authenticator.constitute_password_authentication
        )
        auth_method.assert_called_once_with(user_record)
        self.ds.users().update.assert_called_once_with(user_record)

    def test_reset_user_rejects_system_user(self):
        system_record = UserModel(
            identifier=SYSTEM_USER_IDENTIFIER,
            name=SYSTEM_USER_NAME,
            role=UserRole.SYSTEM,
            state=UserState.ACTIVE,
        )
        self.ds.users().find_by_identifier.return_value = system_record

        with self.assertRaises(UserStateException) as raised:
            self.manager.reset_user(SYSTEM_USER_IDENTIFIER)

        self.assertIn(
            "system user password cannot be reset",
            str(raised.exception),
        )
        self.ds.users().update.assert_not_called()

    def test_reset_user_rejects_unknown_user(self):
        self.ds.users().find_by_identifier.return_value = None

        with self.assertRaises(UserNotFoundException):
            self.manager.reset_user("unknown")

    def test_rotate_shared_secret_updates_settings(self):
        self.manager.rotate_shared_secret("new-secret-value")

        self.ds.settings().update.assert_called_once_with(self.settings)
        self.assertEqual(self.settings.shared_secret, "new-secret-value")

    def test_rotate_shared_secret_rejects_empty_value(self):
        with self.assertRaises(InvalidUserRequestException):
            self.manager.rotate_shared_secret("")

        self.ds.settings().update.assert_not_called()

    def test_get_user_role_raises_domain_exception_for_missing_user(self):
        self.ds.users().find_by_identifier.return_value = None

        with self.assertRaises(UserNotFoundException):
            self.manager.get_user_role("missing-user")

    def test_create_user_requires_shared_secret(self):
        self.ds.users().find_by_identifier.return_value = None
        # pylint: disable=protected-access
        self.settings._shared_secret = ""
        user = User(identifier="new-user", state=UserState.ONBOARDING)

        with self.assertRaises(UserManagementException) as raised:
            self.manager.create_user(user)

        self.assertIn("No shared secret set", str(raised.exception))

    def test_project_manager_uses_domain_exception_for_duplicate_project(self):
        self.ds.projects().find_by_identifier.return_value = object()

        with self.assertRaises(ProjectManagementException):
            ProjectManager().create_project(Project(identifier="duplicate"))

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

    def test_sign_up_user_accepts_reset_state(self):
        user_record = UserModel(
            identifier="reset-user",
            name="Reset User",
            password="hashed-shared-secret",
            role=UserRole.USER,
            state=UserState.RESET,
        )
        self.ds.users().find_by_identifier.return_value = user_record
        user = User(identifier="reset-user", password="new-password")

        self.manager.sign_up_user(user)

        self.assertEqual(user.state, UserState.ACTIVE)
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

    def test_delete_user_prevents_self_deletion(self):
        user_record = UserModel(
            identifier="requester",
            name="Requester",
            role=UserRole.USER,
            state=UserState.ACTIVE,
        )
        self.ds.users().find_by_identifier.return_value = user_record

        with self.assertRaises(UserStateException) as raised:
            self.manager.delete_user(
                User(identifier="requester"),
                requesting_user_id="requester",
            )

        self.assertIn("cannot delete themselves", str(raised.exception))
        self.ds.users().delete_by_identifier.assert_not_called()

    def test_delete_user_prevents_last_active_admin_deletion(self):
        admin_record = UserModel(
            identifier="admin1",
            name="Admin",
            role=UserRole.ADMINISTRATOR,
            state=UserState.ACTIVE,
        )
        self.ds.users().find_by_identifier.return_value = admin_record
        self.ds.users().read_all.return_value = [admin_record]

        with self.assertRaises(UserStateException) as raised:
            self.manager.delete_user(User(identifier="admin1"))

        self.assertIn("active administrator must remain", str(raised.exception))
        self.ds.users().delete_by_identifier.assert_not_called()

    def test_delete_user_prevents_deletion_when_only_reset_admin_remains(self):
        reset_admin = UserModel(
            identifier="admin1",
            name="Admin",
            role=UserRole.ADMINISTRATOR,
            state=UserState.RESET,
        )
        self.ds.users().find_by_identifier.return_value = reset_admin
        self.ds.users().read_all.return_value = [reset_admin]

        with self.assertRaises(UserStateException) as raised:
            self.manager.delete_user(User(identifier="admin1"))

        self.assertIn("active administrator must remain", str(raised.exception))
        self.ds.users().delete_by_identifier.assert_not_called()

    def test_delete_user_allows_admin_deletion_when_another_active_admin_exists(
        self,
    ):
        admin1 = UserModel(
            identifier="admin1",
            name="Admin 1",
            role=UserRole.ADMINISTRATOR,
            state=UserState.ACTIVE,
        )
        admin2 = UserModel(
            identifier="admin2",
            name="Admin 2",
            role=UserRole.ADMINISTRATOR,
            state=UserState.ACTIVE,
        )
        self.ds.users().find_by_identifier.return_value = admin1
        self.ds.users().read_all.return_value = [admin1, admin2]

        self.manager.delete_user(User(identifier="admin1"))

        self.ds.users().delete_by_identifier.assert_called_once_with("admin1")

    def test_set_user_permission_updates_record(self):
        user_record = UserModel(
            identifier="test-user",
            name="Test User",
        )
        permission = UserPermission(
            user=user_record,
            allow_overwrite=False,
        )
        self.ds.users().find_by_identifier.return_value = user_record
        self.ds.users().find_permission.return_value = permission

        self.manager.set_user_permission(
            User(identifier="test-user"),
            UserPermissionKey.ALLOW_OVERWRITE,
            "yes",
        )

        self.assertTrue(permission.allow_overwrite)
        self.ds.users().update_permission.assert_called_once_with(permission)

    def test_set_user_permission_requires_permission_key_enum(self):
        with self.assertRaises(TypeError):
            self.manager.set_user_permission(
                User(identifier="test-user"),
                cast(UserPermissionKey, "unknown_permission"),
                "true",
            )

    def test_set_user_permission_rejects_missing_user(self):
        self.ds.users().find_by_identifier.return_value = None

        with self.assertRaises(UserNotFoundException):
            self.manager.set_user_permission(
                User(identifier="missing-user"),
                UserPermissionKey.ALLOW_OVERWRITE,
                "true",
            )

    def test_set_user_permission_rejects_system_user(self):
        user_record = UserModel(
            identifier=SYSTEM_USER_IDENTIFIER,
            name=SYSTEM_USER_NAME,
            role=UserRole.SYSTEM,
        )
        self.ds.users().find_by_identifier.return_value = user_record

        with self.assertRaises(UserStateException) as raised:
            self.manager.set_user_permission(
                User(identifier=SYSTEM_USER_IDENTIFIER),
                UserPermissionKey.ALLOW_OVERWRITE,
                "false",
            )

        self.assertIn(
            "system user cannot be changed",
            str(raised.exception),
        )
        self.ds.users().find_permission.assert_not_called()
        self.ds.users().update_permission.assert_not_called()

    def test_set_user_permission_rejects_invalid_boolean_value(self):
        user_record = UserModel(
            identifier="test-user",
            name="Test User",
        )
        permission = UserPermission(
            user=user_record,
            allow_overwrite=False,
        )
        self.ds.users().find_by_identifier.return_value = user_record
        self.ds.users().find_permission.return_value = permission

        with self.assertRaises(InvalidUserRequestException) as raised:
            self.manager.set_user_permission(
                User(identifier="test-user"),
                UserPermissionKey.ALLOW_OVERWRITE,
                "enabled",
            )

        self.assertIn("Invalid value 'enabled'", str(raised.exception))

    def test_get_user_permission_returns_current_value(self):
        user_record = UserModel(
            identifier="test-user",
            name="Test User",
        )
        permission = UserPermission(
            user=user_record,
            allow_overwrite=True,
        )
        self.ds.users().find_by_identifier.return_value = user_record
        self.ds.users().find_permission.return_value = permission

        value = self.manager.get_user_permission(
            User(identifier="test-user"),
            UserPermissionKey.ALLOW_OVERWRITE,
        )

        self.assertEqual(value, "True")
        self.ds.users().find_permission.assert_called_once_with(user_record)

    def test_get_user_permission_rejects_missing_user(self):
        self.ds.users().find_by_identifier.return_value = None

        with self.assertRaises(UserNotFoundException):
            self.manager.get_user_permission(
                User(identifier="missing-user"),
                UserPermissionKey.ALLOW_OVERWRITE,
            )

    def test_get_user_permission_requires_permission_key_enum(self):
        with self.assertRaises(TypeError):
            self.manager.get_user_permission(
                User(identifier="test-user"),
                cast(UserPermissionKey, "unknown_permission"),
            )


if __name__ == "__main__":
    TestCase.run_tests()
