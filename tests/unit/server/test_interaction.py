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
"""Unit tests for the interaction module."""

from raven.fathom.base import ClientRequest, Interaction, ServerResponse
from raven.fathom.base import ResponseMessage, ResponseCode, User as BaseUser
from raven.fathom.base.user import UserState
from raven.fathom.base import ClientAuthentication
from raven.fathom.server.interaction import ServerConnectionImpl
from raven.fathom.server.security import UserAuthenticator, UserAuthentication
from raven.fathom.server.models import User
from raven.fathom.server.handlers import HandlerFactory

from tests.unit import TestCase
from tests.unit.mocks import Mock


class TestServerConnection(TestCase):
    """Unit tests for the server-side implementation of
    the `ServerConnection` interface.
    """

    def setUp(self):
        super().setUp()
        self.user = User(
            identifier="test-user-1",
            name="The Test User 1",
        )
        self.authenticator = Mock(spec_set=UserAuthenticator)
        self.handler_factory = Mock(spec_set=HandlerFactory)
        self.connection = ServerConnectionImpl(
            self.authenticator,
            self.handler_factory
        )
        self.request = ClientRequest(Interaction.REQUEST_DEPLOYMENT)
        self.request.authentication = ClientAuthentication(
            username="test-user-1",
            password="test-password-1",
        )
        self.handler_mock = Mock()
        self.handler_factory.create_action_handler_for.return_value = (
            self.handler_mock
        )

    def test_authenticated_request_is_dispatched_to_action_handler(self):
        self.authenticator.authenticate_client.return_value = (
            UserAuthentication(self.user, is_authenticated=True)
        )
        response = self.connection.process(self.request)
        self.assertIsInstance(response, ServerResponse)
        self.assertEqual(response.action, self.request.action)
        self.handler_mock.handle.assert_called_once()
        self.assertIs(self.handler_mock.handle.call_args.args[0], self.request)
        self.assertIs(self.handler_mock.handle.call_args.args[1], response)

    def test_unauthenticated_request_returns_denied_response(self):
        self.authenticator.authenticate_client.return_value = (
            UserAuthentication(user=None, is_authenticated=False)
        )
        response = self.connection.process(self.request)
        self.assertIsInstance(response, ServerResponse)
        self.assertEqual(response.action, self.request.action)
        self.assertTrue(response.has_errors())
        denied_error = response.errors[0]
        self.assertIsInstance(denied_error, ResponseMessage)
        self.assertEqual(denied_error.code, ResponseCode.NOT_AUTHENTICATED)
        self.assertIn("Invalid username or password", denied_error.text)
        method_mock = self.handler_factory.create_action_handler_for
        method_mock.assert_not_called()

    def test_action_handler_for_request_is_provided_by_factory(self):
        self.authenticator.authenticate_client.return_value = (
            UserAuthentication(self.user, is_authenticated=True)
        )
        response = self.connection.process(self.request)
        self.assertIsInstance(response, ServerResponse)
        self.assertEqual(response.action, self.request.action)
        method_mock = self.handler_factory.create_action_handler_for
        method_mock.assert_called_once()
        self.assertIs(method_mock.call_args.args[0], self.request)

    def test_onboarding_user_is_blocked_from_non_setup_action(self):
        self.request.user = BaseUser(
            identifier="test-user-1",
            name="The Test User 1",
            state=UserState.ONBOARDING,
        )
        self.authenticator.authenticate_client.return_value = (
            UserAuthentication(user=None, is_authenticated=False)
        )

        response = self.connection.process(self.request)

        self.assertIsInstance(response, ServerResponse)
        self.assertTrue(response.has_errors())
        self.assertEqual(
            response.errors[0].code,
            ResponseCode.NOT_AUTHENTICATED,
        )
        self.assertIn("Invalid username or password", response.errors[0].text)
        self.handler_factory.create_action_handler_for.assert_not_called()


if __name__ == "__main__":
    TestCase.run_tests()
