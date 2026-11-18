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
for client deployment intents.
"""

from raven.fathom.base import TypeCheck
from raven.fathom.base import ResponseMessage, ResponseCode
from raven.fathom.base import ClientRequest, ServerResponse
from raven.fathom.server.handlers import ActionHandler
from raven.fathom.server.security import DeploymentAuthorizer
from raven.fathom.server.domain import DeploymentManager
from raven.fathom.server.core.logging import Logger


LOG = Logger.get()


class DeploymentIntentHandler(ActionHandler):
    """Implementation of `ActionHandler` for deployment intents."""

    def __init__(
        self,
        authorizer: DeploymentAuthorizer,
        manager: DeploymentManager
    ):
        super().__init__(authorizer=None)
        TypeCheck.require_arg(authorizer, DeploymentAuthorizer)
        self._authorizer = authorizer
        self._manager = manager

    def handle(self, request: ClientRequest, response: ServerResponse):
        intent = request.deployment_intent
        if intent is None:
            response.add_error(
                ResponseMessage(
                    code=ResponseCode.INCOMPLETE_REQUEST,
                    text="No deployment intent provided"
                )
            )
            return

        intent.user = request.authenticated_user
        intent.project = request.project
        if not self._project_info_is_set(intent):
            response.add_error(
                ResponseMessage(
                    code=ResponseCode.INCOMPLETE_REQUEST,
                    text="Project version is not specified"
                )
            )
            return

        result = ""
        authorization = self._authorizer.authorize_intent(intent)
        if authorization.is_granted():
            result = self._manager.can_deploy(intent)
            if result.ok:
                response.add_informational(
                    ResponseMessage(
                        code=ResponseCode.SUCCESSFUL_COMPLETION,
                        text="Deployment authorization has been granted."
                    )
                )
            else:
                authorization.reject(result.user_message)

        LOG.i(
            "User %s requested a deployment of resources for project %s: "
            "%s %s",
            request.authenticated_user_id,
            request.project,
            authorization,
            result and result.user_message,
        )
        response.deployment_authorization = authorization

    def _project_info_is_set(self, intent):
        return (
            intent.project
            and intent.project.version
            and intent.project.version.identifier
        )
