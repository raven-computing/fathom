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
from raven.fathom.base import UserState
from raven.fathom.server.security import UserAuthorizer
from raven.fathom.server.user_management import UserManager

from .handler import ActionHandler


def _deny_unless_admin(
    authorizer: UserAuthorizer,
    request: ClientRequest,
    response: ServerResponse,
) -> bool:
    user = request.user
    if user is not None and authorizer.is_administrator(user):
        return False

    response.add_error(
        ResponseMessage(
            code=ResponseCode.AUTHORIZATION_DENIED,
            text="Administrative privileges are required.",
        )
    )
    return True


class UserCreateHandler(ActionHandler):
    """Handles remote user creation requests."""

    def __init__(self, authorizer: UserAuthorizer, manager: UserManager):
        self._authorizer = authorizer
        self._manager = manager

    def handle(self, request: ClientRequest, response: ServerResponse):
        if _deny_unless_admin(self._authorizer, request, response):
            return

        user = request.managed_user
        if user is None or not user.identifier:
            response.add_error(
                ResponseMessage(
                    code=ResponseCode.INCOMPLETE_REQUEST,
                    text="No managed user identifier provided.",
                )
            )
            return

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

        try:
            self._manager.create_user(user)
        except ValueError as ex:
            response.add_error(
                ResponseMessage(
                    code=ResponseCode.INCOMPLETE_REQUEST,
                    text=str(ex),
                )
            )
            return

        response.managed_users = [user]


class UserSetupHandler(ActionHandler):
    """Handles remote user onboarding setup requests."""

    def __init__(self, manager: UserManager):
        self._manager = manager

    def handle(self, request: ClientRequest, response: ServerResponse):
        user = request.managed_user
        if user is None or not user.identifier:
            response.add_error(
                ResponseMessage(
                    code=ResponseCode.INCOMPLETE_REQUEST,
                    text="No managed user identifier provided.",
                )
            )
            return

        if not user.password:
            response.add_error(
                ResponseMessage(
                    code=ResponseCode.INCOMPLETE_REQUEST,
                    text="No managed user password provided.",
                )
            )
            return

        try:
            self._manager.setup_user(user)
        except ValueError as ex:
            response.add_error(
                ResponseMessage(
                    code=ResponseCode.INCOMPLETE_REQUEST,
                    text=str(ex),
                )
            )
            return

        response.managed_users = [user]


class UserListHandler(ActionHandler):
    """Handles remote user listing requests."""

    def __init__(self, authorizer: UserAuthorizer, manager: UserManager):
        self._authorizer = authorizer
        self._manager = manager

    def handle(self, request: ClientRequest, response: ServerResponse):
        if _deny_unless_admin(self._authorizer, request, response):
            return

        response.managed_users = self._manager.list_users()


class UserDeleteHandler(ActionHandler):
    """Handles remote user deletion requests."""

    def __init__(self, authorizer: UserAuthorizer, manager: UserManager):
        self._authorizer = authorizer
        self._manager = manager

    def handle(self, request: ClientRequest, response: ServerResponse):
        if _deny_unless_admin(self._authorizer, request, response):
            return

        user = request.managed_user
        if user is None or not user.identifier:
            response.add_error(
                ResponseMessage(
                    code=ResponseCode.INCOMPLETE_REQUEST,
                    text="No managed user identifier provided.",
                )
            )
            return

        try:
            self._manager.delete_user(user)
        except ValueError as ex:
            response.add_error(
                ResponseMessage(
                    code=ResponseCode.NOT_FOUND,
                    text=str(ex),
                )
            )
