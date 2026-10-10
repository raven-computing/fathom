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
"""Declares an abstract base class for server action handlers.

Provides an accompanying decorator for enforcing admin-user authorization.
Implementations of `ActionHandler` that require administrative privileges may
use the `@require_admin_privileges` decorator on their `handle()` method to
enforce that the underlying user has administrative access.
"""

import functools

from abc import ABC, abstractmethod
from typing import Optional, TypeAlias, TypeVar, cast
from typing import Callable, Concatenate, ParamSpec

from raven.fathom.base import ClientRequest, ServerResponse
from raven.fathom.base import ResponseCode, ResponseMessage
from raven.fathom.server.security import UserAuthorizer


class ActionHandler(ABC):
    """A server action handler.

    Handles a concrete client-server-interaction and produces
    the corresponding server response.
    """

    def __init__(self, authorizer: Optional[UserAuthorizer] = None):
        """Initializes a new `ActionHandler` instance.

        Args:
            authorizer (UserAuthorizer): The user authorizer to be used
                by the handler when authorization ought to be enforced for
                a specific user role. Defaults to `None`, which means
                no restrictions based on the user role are enforced.
        """
        self._authorizer = authorizer

    @abstractmethod
    def handle(self, request: ClientRequest, response: ServerResponse):
        """Handles the client-server-interaction.

        Args:
            request (ClientRequest): The client request of the interaction.
            response (ServerResponse): The server response of the interaction.

        Raises:
            Exception: If an error occurs while handling the interaction that
                could not be handled by the server by creating an appropriate
                response.
        """


H = TypeVar("H", bound=ActionHandler)

P = ParamSpec("P")

HandleMethod: TypeAlias = Callable[Concatenate[H, P], None]


def require_admin_privileges(method: HandleMethod[H, P]) -> HandleMethod[H, P]:
    """Decorator that enforces successful admin-user authentication.

    Ensures that the decorated `ActionHandler.handle()` method is only executed
    if the authenticated user has administrative privileges. If the user
    does not have the required privileges, an appropriate error
    response is added to the server response.
    """
    @functools.wraps(method)
    def wrapped(
        instance: H,
        request: ClientRequest,
        response: ServerResponse
    ) -> None:
        authorizer = instance._authorizer  # pylint: disable=protected-access
        assert authorizer is not None, (
            "Programming error: When using the @require_admin_privileges "
            "decorator the ActionHandler must be initialized with "
            "a UserAuthorizer"
        )
        if authorizer is not None:
            user = request.authenticated_user
            if user is not None and authorizer.is_administrator(user):
                method(instance, request, response)  # type: ignore
                return

        response.add_error(
            ResponseMessage(
                code=ResponseCode.AUTHORIZATION_DENIED,
                text="Administrative privileges are required.",
            )
        )
        return

    return cast(HandleMethod[H, P], wrapped)
