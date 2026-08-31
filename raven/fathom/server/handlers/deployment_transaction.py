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
from raven.fathom.server.logging import Logger
from raven.fathom.server.handlers import ActionHandler
from raven.fathom.server.security import DeploymentAuthorizer
from raven.fathom.server.deployment import DeploymentManager
from raven.fathom.server.deployment import DeploymentExecutionException


LOG = Logger.get()

AUTHORIZATION_CHECK_FAILED: Final = None


class DeploymentTransactionHandler(ActionHandler):
    """Implementation of `ActionHandler` for deployment transactions."""

    def __init__(self, auth: DeploymentAuthorizer, manager: DeploymentManager):
        TypeCheck.require_arg(auth, DeploymentAuthorizer)
        TypeCheck.require_arg(manager, DeploymentManager)
        self._authorizer = auth
        self._deployment_manager = manager

    def handle(self, request, response):
        authorization = self._check_authorization(request, response)
        if authorization is AUTHORIZATION_CHECK_FAILED:
            return

        package = request.package
        if package is None:
            self._respond_missing_package(response)
            return

        self._handle_deployment(authorization, package, response)

    def _check_authorization(self, request, response):
        alleged = request.deployment_authorization
        if alleged is None or not alleged.token:
            self._respond_missing_auth(response)
            return AUTHORIZATION_CHECK_FAILED

        authorization = self._authorizer.check_authorization(alleged.token)
        if not authorization.is_granted():
            self._respond_auth_denied(response, authorization)
            return AUTHORIZATION_CHECK_FAILED

        return authorization

    def _handle_deployment(self, authorization, package, response):
        intent = authorization.granted_parameters()
        try:
            self._execute_deployment(intent, package, response)
        except DeploymentExecutionException as ex:
            LOG.e(
                "An error occurred during deployment execution "
                "for project %s",
                intent.project
            )
            LOG.e(ex)
            self._respond_failed_deployment(response, ex)

    def _execute_deployment(self, intent, package, response):
        LOG.i("Executing deployment for project %s", intent.project)
        result = self._deployment_manager.deploy(intent, package)
        LOG.i(
            "Deployment for project %s %s",
            intent.project,
            "was successful" if result.successful else "has failed"
        )
        response.deployment_message = DeploymentMessage(
            is_successful=result.successful,
            message=result.user_message,
        )

    def _set_error(self, response, message):
        response.add_error(message)
        response.deployment_message = DeploymentMessage(
            is_successful=False,
            message="Deployment has failed",
        )

    def _respond_failed_deployment(self, response, ex):
        self._set_error(
            response,
            ResponseMessage(
                code=ResponseCode.INTERNAL_ERROR,
                text=str(ex)
            )
        )

    def _respond_missing_package(self, response):
        self._set_error(
            response,
            ResponseMessage(
                code=ResponseCode.INCOMPLETE_REQUEST,
                text="No package provided in deployment transaction"
            )
        )

    def _respond_auth_denied(self, response, authorization):
        self._set_error(
            response,
            ResponseMessage(
                code=ResponseCode.AUTHORIZATION_DENIED,
                text=authorization.status.message()
            )
        )

    def _respond_missing_auth(self, response):
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
