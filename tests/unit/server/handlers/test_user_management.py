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
"""Unit tests for remote user-management handlers."""

from raven.fathom.base import ClientRequest, Interaction, ServerResponse
from raven.fathom.base import ResponseCode, User, UserState
from raven.fathom.server.security import UserAuthorizer
from raven.fathom.server.handlers.user import (
    UserHandler, UserCreateHandler, UserListHandler, UserDeleteHandler,
    UserPermissionGetHandler, UserPermissionSetHandler,
)
from raven.fathom.server.core.user_management import (
    UserManager,
    UserNotFoundException,
    UserStateException,
)

from tests.unit import TestCase
from tests.unit.mocks import Mock


class TestUserManagementHandlers(TestCase):
    """Unit tests for remote user-management handlers."""

    def setUp(self):
        super().setUp()
        self.admin_authorizer = Mock(spec_set=UserAuthorizer)
        self.manager = Mock(spec_set=UserManager)
        self.request_user = User(identifier="alpha-admin", name="Alpha Admin")

    def test_create_handler_rejects_non_admin(self):
        self.admin_authorizer.is_administrator.return_value = False
        request = ClientRequest(Interaction.CREATE_USER)
        request.authenticated_user = self.request_user
        response = ServerResponse(Interaction.CREATE_USER)

        UserHandler(
            self.admin_authorizer,
            UserCreateHandler(self.manager),
            "creation of new user"
        ).handle(request, response)

        self.assertEqual(
            response.errors[0].code,
            ResponseCode.AUTHORIZATION_DENIED,
        )
        self.manager.create_user.assert_not_called()

    def test_create_handler_creates_regular_user(self):
        self.admin_authorizer.is_administrator.return_value = True
        self.manager.create_user.return_value = User(
            identifier="someone",
            name="Some User",
            is_admin=False,
        )
        request = ClientRequest(Interaction.CREATE_USER)
        request.authenticated_user = self.request_user
        request.user = User(identifier="someone", name="Some User")
        response = ServerResponse(Interaction.CREATE_USER)

        UserHandler(
            self.admin_authorizer,
            UserCreateHandler(self.manager),
            "creation of new user"
        ).handle(request, response)

        self.assertFalse(response.has_errors())
        assert response.users is not None
        self.assertEqual(len(response.users), 1)
        expected_user = User(
            identifier="someone",
            name="Some User",
            is_admin=False,
            state=UserState.ONBOARDING
        )
        self.manager.create_user.assert_called_once_with(expected_user)

    def test_create_handler_allows_admin_user_creation(self):
        self.admin_authorizer.is_administrator.return_value = True
        request = ClientRequest(Interaction.CREATE_USER)
        request.authenticated_user = self.request_user
        request.user = User(
            identifier="new-admin", name="New Admin", is_admin=True
        )
        response = ServerResponse(Interaction.CREATE_USER)

        UserHandler(
            self.admin_authorizer,
            UserCreateHandler(self.manager),
            "creation of admin user"
        ).handle(request, response)

        self.assertFalse(response.has_errors())
        expected_user = User(
            identifier="new-admin",
            name="New Admin",
            is_admin=True,
            state=UserState.ONBOARDING,
        )
        self.manager.create_user.assert_called_once_with(expected_user)

    def test_list_handler_returns_users(self):
        self.admin_authorizer.is_administrator.return_value = True
        self.manager.list_users.return_value = [
            User(identifier="alpha", name="Alpha", is_admin=True),
        ]
        request = ClientRequest(Interaction.LIST_USERS)
        request.authenticated_user = self.request_user
        response = ServerResponse(Interaction.LIST_USERS)

        UserHandler(
            self.admin_authorizer,
            UserListHandler(self.manager),
            "listing of registered users"
        ).handle(request, response)

        self.assertFalse(response.has_errors())
        self.assertEqual(
            response.users,
            self.manager.list_users.return_value,
        )

    def test_delete_handler_reports_unknown_user(self):
        self.admin_authorizer.is_administrator.return_value = True
        self.manager.delete_user.side_effect = UserNotFoundException(
            "User 'bla' does not exist"
        )
        request = ClientRequest(Interaction.DELETE_USER)
        request.authenticated_user = self.request_user
        request.user = User(identifier="bla")
        response = ServerResponse(Interaction.DELETE_USER)

        UserHandler(
            self.admin_authorizer,
            UserDeleteHandler(self.manager),
            "deletion of user"
        ).handle(request, response)

        self.assertEqual(response.errors[0].code, ResponseCode.NOT_FOUND)

    def test_delete_handler_passes_requesting_user_id(self):
        self.admin_authorizer.is_administrator.return_value = True
        request = ClientRequest(Interaction.DELETE_USER)
        request.authenticated_user = self.request_user
        request.user = User(identifier="target-user")
        response = ServerResponse(Interaction.DELETE_USER)

        UserHandler(
            self.admin_authorizer,
            UserDeleteHandler(self.manager),
            "deletion of user"
        ).handle(request, response)

        self.manager.delete_user.assert_called_once_with(
            User(identifier="target-user"),
            "alpha-admin",
        )

    def test_delete_handler_rejects_self_deletion(self):
        self.admin_authorizer.is_administrator.return_value = True
        self.manager.delete_user.side_effect = UserStateException(
            "User 'alpha-admin' cannot delete themselves"
        )
        request = ClientRequest(Interaction.DELETE_USER)
        request.authenticated_user = self.request_user
        request.user = User(identifier="alpha-admin")
        response = ServerResponse(Interaction.DELETE_USER)

        UserHandler(
            self.admin_authorizer,
            UserDeleteHandler(self.manager),
            "deletion of user"
        ).handle(request, response)

        self.assertTrue(response.has_errors())
        self.assertEqual(
            response.errors[0].code,
            ResponseCode.INCOMPLETE_REQUEST,
        )

    def test_permission_get_handler_returns_permission_value(self):
        self.admin_authorizer.is_administrator.return_value = True
        self.manager.get_user_permission.return_value = "True"
        request = ClientRequest(Interaction.GET_USER_PERMISSION)
        request.authenticated_user = self.request_user
        request.user = User(identifier="target-user")
        request.permission_key = "allow_overwrite"
        response = ServerResponse(Interaction.GET_USER_PERMISSION)

        UserHandler(
            self.admin_authorizer,
            UserPermissionGetHandler(self.manager),
            "retrieval of user permission",
        ).handle(request, response)

        self.assertFalse(response.has_errors())
        self.assertEqual(response.permission_key, "allow_overwrite")
        self.assertEqual(response.permission_value, "True")

    def test_permission_get_handler_rejects_missing_key(self):
        self.admin_authorizer.is_administrator.return_value = True
        request = ClientRequest(Interaction.GET_USER_PERMISSION)
        request.authenticated_user = self.request_user
        request.user = User(identifier="target-user")
        request.permission_key = None
        response = ServerResponse(Interaction.GET_USER_PERMISSION)

        UserHandler(
            self.admin_authorizer,
            UserPermissionGetHandler(self.manager),
            "retrieval of user permission",
        ).handle(request, response)

        self.assertTrue(response.has_errors())
        self.assertEqual(
            response.errors[0].code,
            ResponseCode.INCOMPLETE_REQUEST,
        )
        self.manager.get_user_permission.assert_not_called()

    def test_permission_set_handler_calls_manager(self):
        self.admin_authorizer.is_administrator.return_value = True
        request = ClientRequest(Interaction.SET_USER_PERMISSION)
        request.authenticated_user = self.request_user
        request.user = User(identifier="target-user")
        request.permission_key = "allow_overwrite"
        request.permission_value = "ON"
        response = ServerResponse(Interaction.SET_USER_PERMISSION)

        UserHandler(
            self.admin_authorizer,
            UserPermissionSetHandler(self.manager),
            "setting of user permission",
        ).handle(request, response)

        self.assertFalse(response.has_errors())
        self.manager.set_user_permission.assert_called_once()

    def test_permission_set_handler_rejects_missing_value(self):
        self.admin_authorizer.is_administrator.return_value = True
        request = ClientRequest(Interaction.SET_USER_PERMISSION)
        request.authenticated_user = self.request_user
        request.user = User(identifier="target-user")
        request.permission_key = "allow_overwrite"
        request.permission_value = None
        response = ServerResponse(Interaction.SET_USER_PERMISSION)

        UserHandler(
            self.admin_authorizer,
            UserPermissionSetHandler(self.manager),
            "setting of user permission",
        ).handle(request, response)

        self.assertTrue(response.has_errors())
        self.assertEqual(
            response.errors[0].code,
            ResponseCode.INCOMPLETE_REQUEST,
        )
        self.manager.set_user_permission.assert_not_called()


if __name__ == "__main__":
    TestCase.run_tests()
