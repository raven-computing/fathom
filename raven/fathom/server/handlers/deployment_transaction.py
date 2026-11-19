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
"""Provides an implementation of the `ActionHandler` class
for deployment transactions.
"""

from typing import Final

from raven.fathom.base import TypeCheck
from raven.fathom.base import ResponseMessage, ResponseCode
from raven.fathom.base import DeploymentMessage
from raven.fathom.base import ClientRequest, ServerResponse
from raven.fathom.base import ProcessingException
from raven.fathom.server.core.logging import Logger
from raven.fathom.server.handlers import ActionHandler
from raven.fathom.server.security import DeploymentAuthorizer
from raven.fathom.server.domain import DeploymentManager
from raven.fathom.server.domain import DeploymentExecutionException


LOG = Logger.get()

AUTHORIZATION_DENIED: Final = None


class DeploymentTransactionHandler(ActionHandler):
    """Implementation of `ActionHandler` for deployment transactions."""

    def __init__(self, auth: DeploymentAuthorizer, manager: DeploymentManager):
        super().__init__(authorizer=None)
        TypeCheck.require_arg(auth, DeploymentAuthorizer)
        TypeCheck.require_arg(manager, DeploymentManager)
        self._authorizer = auth
        self._deployment_manager = manager

    def handle(self, request: ClientRequest, response: ServerResponse):
        authorization = self._check_authorization(request, response)
        if authorization is AUTHORIZATION_DENIED:
            return

        package = request.package
        if package is None:
            self._respond_missing_package(request, response)
            return

        assert authorization is not None
        intent = authorization.granted_parameters()
        assert intent is not None
        LOG.i(
            "User %s requested the execution of deployment for project %s",
            request.authenticated_user_id,
            intent.project,
        )
        if self._handle_deployment(authorization, package, response):
            self._authorizer.clear_authorization(authorization)

    def _check_authorization(self, request, response):
        alleged = request.deployment_authorization
        if alleged is None or not alleged.token:
            self._respond_missing_auth(request, response)
            return AUTHORIZATION_DENIED

        authorization = self._authorizer.check_authorization(alleged.token)
        if not authorization.is_granted():
            self._respond_auth_denied(request, response, authorization)
            return AUTHORIZATION_DENIED

        return authorization

    def _handle_deployment(self, authorization, package, response):
        intent = authorization.granted_parameters()
        try:
            return self._execute_deployment(intent, package, response)
        except DeploymentExecutionException as ex:
            LOG.e(
                "An error occurred during deployment execution "
                "for project %s",
                intent.project
            )
            LOG.e(ex)
            self._respond_failed_deployment(response, ex)

        return False

    def _execute_deployment(self, intent, package, response):
        LOG.i("Executing deployment for project %s", intent.project)
        result = self._deployment_manager.deploy(intent, package)
        LOG.i(
            "Deployment for project %s %s",
            intent.project,
            "was successful" if result.ok else "has failed"
        )
        response.deployment_message = DeploymentMessage(
            is_successful=result.ok,
            message=result.user_message,
        )
        if result.ok:
            response.add_informational(
                ResponseMessage(
                    code=ResponseCode.SUCCESSFUL_COMPLETION,
                    text="Deployment succeeded."
                )
            )

        return result.ok

    def _set_error(self, response, message):
        response.add_error(message)
        response.deployment_message = DeploymentMessage(
            is_successful=False,
            message="Deployment has failed",
        )

    def _respond_failed_deployment(self, response, ex):
        raise ProcessingException(
            "An error has occurred while deploying package"
        )

    def _respond_missing_package(self, request, response):
        LOG.i(
            "User %s requested the execution of a deployment but "
            "did not provide a package to deploy",
            request.authenticated_user_id,
        )
        self._set_error(
            response,
            ResponseMessage(
                code=ResponseCode.INCOMPLETE_REQUEST,
                text="No package provided in deployment transaction"
            )
        )

    def _respond_auth_denied(self, request, response, authorization):
        LOG.i(
            "User %s requested the execution of a deployment but "
            "the provided authorization is not valid: %r",
            request.authenticated_user_id,
            authorization.status,
        )
        self._set_error(
            response,
            ResponseMessage(
                code=ResponseCode.AUTHORIZATION_DENIED,
                text=authorization.status.message()
            )
        )

    def _respond_missing_auth(self, request, response):
        LOG.i(
            "User %s requested the execution of a deployment but "
            "did not provide an authorization token",
            request.authenticated_user_id,
        )
        self._set_error(
            response,
            ResponseMessage(
                code=ResponseCode.MISSING_AUTHORIZATION,
                text=(
                    "Unauthorized deployment transaction: "
                    "Missing authorization token"
                )
            )
        )
