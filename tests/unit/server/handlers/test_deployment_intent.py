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
"""Unit tests for deployment intent handling."""

from raven.fathom.base import (
    ClientDeploymentIntent,
    ClientRequest,
    DeploymentAuthorization,
    Interaction,
    Project,
    ProjectVersion,
    ResponseCode,
    ServerResponse,
    User,
)
from raven.fathom.server.domain import (
    DeploymentManager,
    DeploymentResult,
)
from raven.fathom.server.handlers.deployment_intent import (
    DeploymentIntentHandler,
)
from raven.fathom.server.security import DeploymentAuthorizer

from tests.unit import TestCase
from tests.unit.mocks import Mock


class TestDeploymentIntentHandler(TestCase):
    """Unit tests for the `DeploymentIntentHandler` class."""

    def setUp(self):
        super().setUp()
        self.authorizer = Mock(spec_set=DeploymentAuthorizer)
        self.manager = Mock(spec_set=DeploymentManager)
        self.handler = DeploymentIntentHandler(self.authorizer, self.manager)
        self.user = User("tester", "Tester")
        self.project = Project("demo", version=ProjectVersion("1.2.3"))
        self.request = ClientRequest(Interaction.REQUEST_DEPLOYMENT)
        self.request.authenticated_user = self.user
        self.request.project = self.project
        self.request.deployment_intent = ClientDeploymentIntent(
            project=self.project,
        )
        self.response = ServerResponse(Interaction.REQUEST_DEPLOYMENT)

    def test_handle_missing_deployment_intent(self):
        self.request.deployment_intent = None

        self.handler.handle(self.request, self.response)

        self.assertTrue(self.response.has_errors())
        self.assertEqual(
            self.response.errors[0].code,
            ResponseCode.INCOMPLETE_REQUEST,
        )
        self.assertEqual(
            self.response.errors[0].text,
            "No deployment intent provided",
        )
        self.authorizer.authorize_intent.assert_not_called()
        self.manager.can_deploy.assert_not_called()

    def test_handle_missing_project_version(self):
        self.request.project = Project("demo")
        self.request.deployment_intent = ClientDeploymentIntent(
            project=self.request.project,
        )

        self.handler.handle(self.request, self.response)

        self.assertTrue(self.response.has_errors())
        self.assertEqual(
            self.response.errors[0].code,
            ResponseCode.INCOMPLETE_REQUEST,
        )
        self.assertEqual(
            self.response.errors[0].text,
            "Project version is not specified",
        )
        self.authorizer.authorize_intent.assert_not_called()
        self.manager.can_deploy.assert_not_called()

    def test_handle_successful_intent_allows_deployment(self):
        granted = DeploymentAuthorization.grant(
            self.request.deployment_intent,
            "valid-token",
            expiration_time=True,
        )
        self.authorizer.authorize_intent.return_value = granted
        self.manager.can_deploy.return_value = DeploymentResult(
            ok=True,
            user_message="Can be deployed",
        )

        self.handler.handle(self.request, self.response)

        self.assertTrue(self.response.has_informational())
        self.assertEqual(
            self.response.infos[0].code,
            ResponseCode.SUCCESSFUL_COMPLETION,
        )
        self.assertEqual(
            self.response.infos[0].text,
            "Deployment authorization has been granted.",
        )
        self.authorizer.authorize_intent.assert_called_once_with(
            self.request.deployment_intent,
        )
        self.manager.can_deploy.assert_called_once_with(
            self.request.deployment_intent,
        )
        assert self.request.deployment_intent is not None
        self.assertIs(self.request.deployment_intent.user, self.user)
        self.assertIs(self.request.deployment_intent.project, self.project)
        self.assertIs(self.response.deployment_authorization, granted)
        self.authorizer.revoke_authorization.assert_not_called()

    def test_handle_failed_can_deploy_rejects_authorization(self):
        granted = DeploymentAuthorization.grant(
            self.request.deployment_intent,
            "valid-token",
            expiration_time=True,
        )
        self.authorizer.authorize_intent.return_value = granted
        self.manager.can_deploy.return_value = DeploymentResult(
            ok=False,
            user_message="Deployment is blocked",
        )

        self.handler.handle(self.request, self.response)

        assert self.response.deployment_authorization is not None
        self.assertFalse(self.response.deployment_authorization.is_granted())
        self.assertEqual(
            self.response.deployment_authorization.status,
            DeploymentAuthorization.Status.REJECTED,
        )
        self.assertEqual(
            self.response.deployment_authorization.rejection_reason,
            "Deployment is blocked",
        )
        self.assertFalse(self.response.has_informational())
        self.authorizer.revoke_authorization.assert_called_once_with(granted)


if __name__ == "__main__":
    TestCase.run_tests()
