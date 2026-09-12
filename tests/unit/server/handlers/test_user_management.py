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
from raven.fathom.server.handlers.user_management import (
    UserCreateHandler, UserListHandler, UserDeleteHandler,
)
from raven.fathom.server.security import UserAuthorizer
from raven.fathom.server.user_management import UserManager

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
        request.user = self.request_user
        response = ServerResponse(Interaction.CREATE_USER)

        UserCreateHandler(self.admin_authorizer, self.manager).handle(
            request, response
        )

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
        request.user = self.request_user
        request.managed_user = User(identifier="someone", name="Some User")
        response = ServerResponse(Interaction.CREATE_USER)

        UserCreateHandler(self.admin_authorizer, self.manager).handle(
            request, response
        )

        self.assertFalse(response.has_errors())
        assert response.managed_users is not None
        self.assertEqual(len(response.managed_users), 1)
        expected_user = User(
            identifier="someone",
            name="Some User",
            is_admin=False,
            state=UserState.ONBOARDING
        )
        self.manager.create_user.assert_called_once_with(
            expected_user
        )

    def test_list_handler_returns_managed_users(self):
        self.admin_authorizer.is_administrator.return_value = True
        self.manager.list_users.return_value = [
            User(identifier="alpha", name="Alpha", is_admin=True),
        ]
        request = ClientRequest(Interaction.LIST_USERS)
        request.user = self.request_user
        response = ServerResponse(Interaction.LIST_USERS)

        UserListHandler(self.admin_authorizer, self.manager).handle(
            request, response
        )

        self.assertFalse(response.has_errors())
        self.assertEqual(
            response.managed_users,
            self.manager.list_users.return_value,
        )

    def test_delete_handler_reports_unknown_user(self):
        self.admin_authorizer.is_administrator.return_value = True
        self.manager.delete_user.side_effect = ValueError(
            "User 'bla' does not exist"
        )
        request = ClientRequest(Interaction.DELETE_USER)
        request.user = self.request_user
        request.managed_user = User(identifier="bla")
        response = ServerResponse(Interaction.DELETE_USER)

        UserDeleteHandler(self.admin_authorizer, self.manager).handle(
            request, response
        )

        self.assertEqual(response.errors[0].code, ResponseCode.NOT_FOUND)


if __name__ == "__main__":
    TestCase.run_tests()
