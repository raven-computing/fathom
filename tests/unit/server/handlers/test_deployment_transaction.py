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
"""Unit tests for deployment_transaction module."""

from raven.fathom.base import ClientRequest, Interaction, ServerResponse
from raven.fathom.base import ResponseCode, Package
from raven.fathom.base import DeploymentAuthorization, ClientDeploymentIntent
from raven.fathom.server.security import DeploymentAuthorizer
from raven.fathom.server.deployment import DeploymentManager, DeploymentResult
from raven.fathom.server.deployment import DeploymentExecutionException
from raven.fathom.server.handlers.deployment_transaction import (
    DeploymentTransactionHandler
)

from tests.unit import TestCase
from tests.unit.mocks import Mock


class TestDeploymentTransactionHandler(TestCase):
    """Unit tests for the `DeploymentTransactionHandler` class."""

    def setUp(self):
        self.valid_intent = ClientDeploymentIntent()
        self.deployment_package = Package(b"test_package_data")
        self.mock_authorizer_grant = Mock(spec_set=DeploymentAuthorizer)
        granted_auth = DeploymentAuthorization.grant(
            self.valid_intent, "ValidToken", expiration_time=True,
        )
        self.mock_authorizer_grant.check_authorization.return_value = (
            granted_auth
        )
        self.mock_authorizer_deny = Mock(spec_set=DeploymentAuthorizer)
        denied_auth = DeploymentAuthorization.deny(
            DeploymentAuthorization.Status.INVALID_TOKEN
        )
        self.mock_authorizer_deny.check_authorization.return_value = (
            denied_auth
        )
        self.mock_manager = Mock(spec_set=DeploymentManager)
        self.mock_manager.deploy.return_value = DeploymentResult(
            successful=True,
            user_message="Deployment succeeded",
        )
        self.mock_manager_failure = Mock(spec_set=DeploymentManager)
        self.mock_manager_failure.deploy.return_value = DeploymentResult(
            successful=False,
            user_message="Deployment failed",
        )
        self.client_request = ClientRequest(Interaction.TRANSACT_DEPLOYMENT)
        self.client_request.deployment_authorization = granted_auth
        self.client_request.package = self.deployment_package
        self.server_response = ServerResponse(Interaction.TRANSACT_DEPLOYMENT)

    def test_handle_missing_authorization(self):
        self.client_request.deployment_authorization = None

        handler = DeploymentTransactionHandler(
            self.mock_authorizer_deny, self.mock_manager
        )
        handler.handle(self.client_request, self.server_response)

        error_message = self.server_response.errors[0]
        self.assertEqual(
            error_message.code, ResponseCode.MISSING_AUTHORIZATION
        )
        self.mock_manager.deploy.assert_not_called()

    def test_handle_authorization_denied_due_to_invalid_auth_token(self):
        self.client_request.deployment_authorization = DeploymentAuthorization(
            DeploymentAuthorization.Status.GRANTED,
            intent=None,
            token="InvalidToken",
            expiration_time=None,
        )

        handler = DeploymentTransactionHandler(
            self.mock_authorizer_deny, self.mock_manager
        )
        handler.handle(self.client_request, self.server_response)

        error_message = self.server_response.errors[0]
        self.assertEqual(error_message.code, ResponseCode.AUTHORIZATION_DENIED)
        self.assertEqual(error_message.text, "Authorization token is invalid")
        self.mock_authorizer_deny.check_authorization.assert_called_once()
        self.assertEqual(
            self.mock_authorizer_deny.check_authorization.call_args.args[0],
            "InvalidToken"
        )
        self.mock_manager.deploy.assert_not_called()

    def test_handle_missing_package(self):
        self.client_request.package = None

        handler = DeploymentTransactionHandler(
            self.mock_authorizer_grant, self.mock_manager
        )
        handler.handle(self.client_request, self.server_response)

        error_message = self.server_response.errors[0]
        self.assertEqual(error_message.code, ResponseCode.INCOMPLETE_REQUEST)
        self.assertEqual(
            error_message.text,
            "No package provided in deployment transaction"
        )
        self.mock_manager.deploy.assert_not_called()

    def test_handle_successful_deployment(self):
        handler = DeploymentTransactionHandler(
            self.mock_authorizer_grant, self.mock_manager
        )
        handler.handle(self.client_request, self.server_response)

        self.assertFalse(self.server_response.has_warnings())
        self.assertFalse(self.server_response.has_errors())
        self.assertIsNotNone(self.server_response.deployment_message)
        assert self.server_response.deployment_message is not None
        self.assertTrue(self.server_response.deployment_message.is_successful)
        self.assertEqual(
            self.server_response.deployment_message.message,
            "Deployment succeeded"
        )
        self.mock_manager.deploy.assert_called_once()
        self.assertEqual(
            self.mock_manager.deploy.call_args.args[0],
            self.valid_intent
        )
        self.assertEqual(
            self.mock_manager.deploy.call_args.args[1],
            self.deployment_package
        )

    def test_handle_failed_deployment_without_encountered_exception(self):
        handler = DeploymentTransactionHandler(
            self.mock_authorizer_grant, self.mock_manager_failure
        )
        handler.handle(self.client_request, self.server_response)

        self.assertFalse(self.server_response.has_warnings())
        self.assertFalse(self.server_response.has_errors())
        self.assertIsNotNone(self.server_response.deployment_message)
        assert self.server_response.deployment_message is not None
        self.assertFalse(self.server_response.deployment_message.is_successful)
        self.assertEqual(
            self.server_response.deployment_message.message,
            "Deployment failed"
        )

    def test_handle_deployment_execution_exception(self):
        self.mock_manager_failure.deploy.side_effect = (
            DeploymentExecutionException(
                "Deployment failure exception message"
            )
        )

        handler = DeploymentTransactionHandler(
            self.mock_authorizer_grant, self.mock_manager_failure
        )
        handler.handle(self.client_request, self.server_response)

        error_message = self.server_response.errors[0]
        self.assertEqual(error_message.code, ResponseCode.INTERNAL_ERROR)
        self.assertEqual(
            error_message.text,
            "Deployment failure exception message"
        )
        self.assertIsNotNone(self.server_response.deployment_message)
        assert self.server_response.deployment_message is not None
        self.assertFalse(self.server_response.deployment_message.is_successful)
        self.assertEqual(
            self.server_response.deployment_message.message,
            "Deployment has failed"
        )


if __name__ == "__main__":
    TestCase.run_tests()
