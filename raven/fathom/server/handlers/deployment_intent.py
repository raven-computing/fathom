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
from raven.fathom.server.handlers import ActionHandler
from raven.fathom.server.security import DeploymentAuthorizer


class DeploymentIntentHandler(ActionHandler):
    """Implementation of `ActionHandler` for deployment intents."""

    def __init__(self, authorizer: DeploymentAuthorizer):
        TypeCheck.require_arg(authorizer, DeploymentAuthorizer)
        self._authorizer = authorizer

    def handle(self, request, response):
        intent = request.deployment_intent
        if intent is None:
            response.add_error(
                ResponseMessage(
                    code=ResponseCode.INCOMPLETE_REQUEST,
                    text="No deployment intent provided"
                )
            )
            return

        intent.user = request.user
        intent.project = request.project
        if not self._project_info_is_set(intent):
            response.add_error(
                ResponseMessage(
                    code=ResponseCode.INCOMPLETE_REQUEST,
                    text="Project version is not specified"
                )
            )
            return

        authorization = self._authorizer.authorize_intent(intent)
        response.deployment_authorization = authorization

    def _project_info_is_set(self, intent):
        return (
            intent.project
            and intent.project.version
            and intent.project.version.identifier
        )
