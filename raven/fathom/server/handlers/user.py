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
from raven.fathom.base import UserState
from raven.fathom.server.security import UserAuthorizer
from raven.fathom.server.core.user_management import (
    UserManager,
    UserManagementException,
    UserNotFoundException,
)

from .handler import ActionHandler, require_admin_privileges


class UserCreateHandler(ActionHandler):
    """Handles remote user creation requests."""

    def __init__(self, authorizer: UserAuthorizer, manager: UserManager):
        super().__init__(authorizer)
        self._manager = manager

    @require_admin_privileges
    def handle(self, request: ClientRequest, response: ServerResponse):
        user = request.user
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
        except UserManagementException as ex:
            response.add_error(
                ResponseMessage(
                    code=ResponseCode.INCOMPLETE_REQUEST,
                    text=str(ex),
                )
            )
            return

        response.users = [user]


class UserListHandler(ActionHandler):
    """Handles remote user listing requests."""

    def __init__(self, authorizer: UserAuthorizer, manager: UserManager):
        super().__init__(authorizer)
        self._manager = manager

    @require_admin_privileges
    def handle(self, request: ClientRequest, response: ServerResponse):
        try:
            response.users = self._manager.list_users()
        except UserManagementException as ex:
            raise ProcessingException(
                "Internal error while handling request about user entity"
            ) from ex


class UserDeleteHandler(ActionHandler):
    """Handles remote user deletion requests."""

    def __init__(self, authorizer: UserAuthorizer, manager: UserManager):
        super().__init__(authorizer)
        self._manager = manager

    @require_admin_privileges
    def handle(self, request: ClientRequest, response: ServerResponse):
        user = request.user
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
        except UserNotFoundException as ex:
            response.add_error(
                ResponseMessage(
                    code=ResponseCode.NOT_FOUND,
                    text=str(ex),
                )
            )
        except UserManagementException as ex:
            raise ProcessingException(
                "Internal error while handling request about project entity"
            ) from ex
