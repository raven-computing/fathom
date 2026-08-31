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
"""Server-specific implementations for client-server-interactions."""

from raven.fathom.base import ServerConnection
from raven.fathom.base import Interaction
from raven.fathom.base import ServerResponse, DeploymentAuthorization
from raven.fathom.base import ProcessingException
from raven.fathom.base import ResponseMessage, ResponseCode
from raven.fathom.server.security import UserAuthenticator
from raven.fathom.server.handlers import HandlerFactory


class ServerConnectionImpl(ServerConnection):
    """Server implementation of the `ServerConnection` interface.

    Enforces client authentication. Dispatches incoming client requests
    to the corresponding handlers.
    """

    def __init__(
        self,
        user_authenticator: UserAuthenticator,
        handler_factory: HandlerFactory
    ):
        super().__init__()
        self._authenticator = user_authenticator
        self._factory = handler_factory

    def process(self, request):
        response = ServerResponse(request.action)

        user = self._authenticator.authenticate_client(request)
        if not user.is_authenticated():
            return self._unauthenticated(response)

        handler = self._factory.create_action_handler_for(request)
        if handler is None:
            raise ProcessingException(f"Unknown action {request.action}")

        handler.handle(request, response)
        return response

    def _unauthenticated(self, response):
        if response.action == Interaction.REQUEST_DEPLOYMENT:
            response.deployment_authorization = DeploymentAuthorization.deny(
                DeploymentAuthorization.Status.INVALID_USER
            )

        response.add_error(
            ResponseMessage(
                code=ResponseCode.NOT_AUTHENTICATED,
                text="Invalid username or password.",
            )
        )
        return response
