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

from raven.fathom.base import ServerInteraction
from raven.fathom.base import Interaction
from raven.fathom.base import ClientRequest, ServerResponse
from raven.fathom.base import DeploymentAuthorization
from raven.fathom.base import ProcessingException
from raven.fathom.base import ResponseMessage, ResponseCode
from raven.fathom.server.security import UserAuthenticator
from raven.fathom.server.handlers import HandlerFactory
from raven.fathom.server.core.logging import Logger, LogLevel


LOG = Logger.get()


class ServerInteractionImpl(ServerInteraction):
    """Server implementation of the `ServerInteraction` interface.

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

    def process(self, request: ClientRequest) -> ServerResponse:
        response = ServerResponse(request.action)

        user = self._authenticator.authenticate_client(request)
        if not user.is_authenticated():
            return self._unauthenticated(request, response, user)

        handler = self._factory.create_action_handler_for(request)
        if handler is None:
            raise ProcessingException(f"Unknown action {request.action}")

        handler.handle(request, response)

        self._log_interaction(request, response)
        return response

    def _unauthenticated(self, request, response, auth):
        user_id = (
            request.authentication.username
            if request.authentication is not None
            else "<unknown>"
        )
        reason = auth.reason or "<unspecified>"
        LOG.i(
            "Unauthenticated client request %s by user %s. Reason: %s",
            response.action,
            user_id,
            reason,
        )
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

    def _log_interaction(self, request, response):
        if LOG.has_level(LogLevel.VERBOSE):
            LOG.v(
                "Responding to %s request of user %s with %s",
                request.action,
                request.authenticated_user_id,
                response.get_all_codes()
            )
