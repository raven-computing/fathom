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
"""Handlers for remote project-management interactions."""

from raven.fathom.base import ClientRequest, ServerResponse
from raven.fathom.base import ResponseCode, ResponseMessage
from raven.fathom.server.security import UserAuthorizer
from raven.fathom.server.project_management import ProjectManager

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


class ProjectCreateHandler(ActionHandler):
    """Handles remote project creation requests."""

    def __init__(self, authorizer: UserAuthorizer, manager: ProjectManager):
        self._authorizer = authorizer
        self._manager = manager

    def handle(self, request: ClientRequest, response: ServerResponse):
        if _deny_unless_admin(self._authorizer, request, response):
            return

        project = request.managed_project
        if project is None or not project.identifier:
            response.add_error(
                ResponseMessage(
                    code=ResponseCode.INCOMPLETE_REQUEST,
                    text="No managed project identifier provided.",
                )
            )
            return

        try:
            self._manager.create_project(project)
        except ValueError as ex:
            response.add_error(
                ResponseMessage(
                    code=ResponseCode.INCOMPLETE_REQUEST,
                    text=str(ex),
                )
            )
            return

        response.managed_projects = [project]


class ProjectListHandler(ActionHandler):
    """Handles remote project listing requests."""

    def __init__(self, authorizer: UserAuthorizer, manager: ProjectManager):
        self._authorizer = authorizer
        self._manager = manager

    def handle(self, request: ClientRequest, response: ServerResponse):
        if _deny_unless_admin(self._authorizer, request, response):
            return

        response.managed_projects = self._manager.list_projects()


class ProjectDeleteHandler(ActionHandler):
    """Handles remote project deletion requests."""

    def __init__(self, authorizer: UserAuthorizer, manager: ProjectManager):
        self._authorizer = authorizer
        self._manager = manager

    def handle(self, request: ClientRequest, response: ServerResponse):
        if _deny_unless_admin(self._authorizer, request, response):
            return

        project = request.managed_project
        if project is None or not project.identifier:
            response.add_error(
                ResponseMessage(
                    code=ResponseCode.INCOMPLETE_REQUEST,
                    text="No managed project identifier provided.",
                )
            )
            return

        try:
            self._manager.delete_project(project)
        except ValueError as ex:
            response.add_error(
                ResponseMessage(
                    code=ResponseCode.NOT_FOUND,
                    text=str(ex),
                )
            )
