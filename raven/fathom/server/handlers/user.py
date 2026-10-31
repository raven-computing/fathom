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
"""Handlers for remote user-management interactions."""

from raven.fathom.base import ClientRequest, ServerResponse
from raven.fathom.base import ResponseCode, ResponseMessage
from raven.fathom.base import ProcessingException
from raven.fathom.base import User, UserState
from raven.fathom.server.core.logging import Logger
from raven.fathom.server.security import UserAuthorizer
from raven.fathom.server.core.user_management import (
    UserManager,
    UserManagementException,
    UserNotFoundException,
    UserInternalException,
)

from .handler import ActionHandler, require_admin_privileges


LOG = Logger.get()


def _has_user_identifier_set(
    user: User | None,
    response: ServerResponse
) -> bool:
    if user is None or not user.identifier:
        response.add_error(
            ResponseMessage(
                code=ResponseCode.INCOMPLETE_REQUEST,
                text="No managed user identifier provided.",
            )
        )
        return False

    return True


class UserHandler(ActionHandler):
    """An `ActionHandler` that wraps another `ActionHandler` to handle
    all exceptions of type `UserManagementException` and to enforce
    that the user making the request has admin privileges.
    """

    def __init__(
        self,
        authorizer: UserAuthorizer,
        action: ActionHandler,
        action_term: str
    ):
        """Initializes a new `UserHandler` instance to wrap
        the given `ActionHandler`.

        Args:
            authorizer (UserAuthorizer): The user authorizer to use
                for admin-privilege checks.
            action (ActionHandler): The action to delegate to.
            action_term (str): Description of the action. Is used for logging.
        """
        super().__init__(authorizer)
        self._action = action
        self._action_term = action_term

    @require_admin_privileges
    def handle(self, request: ClientRequest, response: ServerResponse):
        user = request.user
        user_id = user.identifier + " " if user is not None else ""
        try:
            self._action.handle(request, response)
        except UserNotFoundException as ex:
            response.add_error(
                ResponseMessage(
                    code=ResponseCode.NOT_FOUND,
                    text=str(ex),
                )
            )
            LOG.i(
                "User %s requested %s %s"
                "but no such user exists",
                request.authenticated_user_id,
                self._action_term,
                user_id,
            )
            return
        except UserInternalException as ex:
            LOG.e(
                "User %s requested %s %s"
                "but an internal error has occurred:",
                request.authenticated_user_id,
                self._action_term,
                user_id,
            )
            LOG.e(ex)
            raise ProcessingException(
                "Internal error while handling request about user entity"
            ) from ex
        except UserManagementException as ex:
            response.add_error(
                ResponseMessage(
                    code=ResponseCode.INCOMPLETE_REQUEST,
                    text=str(ex),
                )
            )
            LOG.i(
                "User %s requested %s %s"
                "but the operation was rejected: %s",
                request.authenticated_user_id,
                self._action_term,
                user_id,
                str(ex),
            )
            return


class UserCreateHandler(ActionHandler):
    """Handles remote user creation requests."""

    def __init__(self, manager: UserManager):
        super().__init__(None)
        self._manager = manager

    def handle(self, request: ClientRequest, response: ServerResponse):
        user = request.user
        if not _has_user_identifier_set(user, response):
            return

        assert user is not None
        if user.is_admin:
            response.add_error(
                ResponseMessage(
                    code=ResponseCode.AUTHORIZATION_DENIED,
                    text=(
                        "Remote user creation cannot grant "
                        "administrator permissions."
                    ),
                )
            )
            return

        user.state = UserState.ONBOARDING

        self._manager.create_user(user)
        LOG.i(
            "User %s created new user %s",
            request.authenticated_user_id,
            user.identifier,
        )
        response.users = [user]


class UserListHandler(ActionHandler):
    """Handles remote user listing requests."""

    def __init__(self, manager: UserManager):
        super().__init__(None)
        self._manager = manager

    def handle(self, request: ClientRequest, response: ServerResponse):
        response.users = self._manager.list_users()
        LOG.i(
            "User %s requested to view a list of all registered users",
            request.authenticated_user_id,
        )


class UserDeleteHandler(ActionHandler):
    """Handles remote user deletion requests."""

    def __init__(self, manager: UserManager):
        super().__init__(None)
        self._manager = manager

    def handle(self, request: ClientRequest, response: ServerResponse):
        user = request.user
        if not _has_user_identifier_set(user, response):
            return

        assert user is not None

        self._manager.delete_user(user)
        LOG.i(
            "User %s deleted user %s",
            request.authenticated_user_id,
            user.identifier,
        )
