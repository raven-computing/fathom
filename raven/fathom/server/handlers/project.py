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
from raven.fathom.server.core.logging import Logger
from raven.fathom.server.security import UserAuthorizer
from raven.fathom.server.domain.project import (
    ProjectManager,
    ProjectManagementException,
    ProjectNotFoundException,
    ProjectInternalException,
)

from .handler import ActionHandler, require_admin_privileges


LOG = Logger.get()


class ProjectHandler(ActionHandler):
    """An `ActionHandler` that wraps another `ActionHandler` to handle
    all exceptions of type `ProjectManagementException` and to enforce
    that the user making the request has admin privileges.
    """

    def __init__(
        self,
        authorizer: UserAuthorizer,
        action: ActionHandler,
        action_term: str
    ):
        """Initializes a new `ProjectHandler` instance to wrap
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
        project = request.project
        project_id = project.identifier + " " if project is not None else ""
        try:
            self._action.handle(request, response)
        except ProjectNotFoundException as ex:
            response.add_error(
                ResponseMessage(
                    code=ResponseCode.NOT_FOUND,
                    text=str(ex),
                )
            )
            LOG.i(
                "User %s requested %s %s"
                "but no such project exists",
                request.authenticated_user_id,
                self._action_term,
                project_id,
            )
            return
        except ProjectInternalException as ex:
            response.add_error(
                ResponseMessage(
                    code=ResponseCode.INTERNAL_ERROR,
                    text="An internal server error has occurred.",
                )
            )
            LOG.e(
                "User %s requested %s %s"
                "but an internal error has occurred: %s",
                request.authenticated_user_id,
                self._action_term,
                project_id,
                str(ex),
            )
            LOG.e(ex)
            return
        except ProjectManagementException as ex:
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
                project_id,
                str(ex),
            )
            return


class ProjectCreateHandler(ActionHandler):
    """Handles remote project creation requests."""

    def __init__(self, manager: ProjectManager):
        super().__init__(None)
        self._manager = manager

    def handle(self, request: ClientRequest, response: ServerResponse):
        project = request.project
        if project is None or not project.identifier:
            response.add_error(
                ResponseMessage(
                    code=ResponseCode.INCOMPLETE_REQUEST,
                    text="No managed project identifier provided.",
                )
            )
            return

        self._manager.create_project(project)
        LOG.i(
            "User %s created new project %s",
            request.authenticated_user_id,
            project.identifier,
        )
        response.projects = [project]


class ProjectListHandler(ActionHandler):
    """Handles remote project listing requests."""

    def __init__(self, manager: ProjectManager):
        super().__init__(None)
        self._manager = manager

    def handle(self, request: ClientRequest, response: ServerResponse):
        response.projects = self._manager.list_projects()
        LOG.i(
            "User %s requested to view a list of all available projects",
            request.authenticated_user_id,
        )


class ProjectUserListHandler(ActionHandler):
    """Handles remote project-user listing requests."""

    def __init__(self, manager: ProjectManager):
        super().__init__(None)
        self._manager = manager

    def handle(self, request: ClientRequest, response: ServerResponse):
        project = request.project
        if project is None or not project.identifier:
            response.add_error(
                ResponseMessage(
                    code=ResponseCode.INCOMPLETE_REQUEST,
                    text="No managed project identifier provided.",
                )
            )
            return

        response.users = self._manager.list_project_users(project)
        LOG.i(
            "User %s requested to view a list of users assigned to project %s",
            request.authenticated_user_id,
            project.identifier,
        )


class ProjectUserAssignHandler(ActionHandler):
    """Handles remote project-user assignment requests."""

    def __init__(self, manager: ProjectManager):
        super().__init__(None)
        self._manager = manager

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

        project = request.project
        if project is None or not project.identifier:
            response.add_error(
                ResponseMessage(
                    code=ResponseCode.INCOMPLETE_REQUEST,
                    text="No managed project identifier provided.",
                )
            )
            return

        self._manager.assign_user_to_project(user, project)
        LOG.i(
            "User %s assigned user %s to project %s",
            request.authenticated_user_id,
            user.identifier,
            project.identifier,
        )


class ProjectUserUnassignHandler(ActionHandler):
    """Handles remote project-user unassignment requests."""

    def __init__(self, manager: ProjectManager):
        super().__init__(None)
        self._manager = manager

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

        project = request.project
        if project is None or not project.identifier:
            response.add_error(
                ResponseMessage(
                    code=ResponseCode.INCOMPLETE_REQUEST,
                    text="No managed project identifier provided.",
                )
            )
            return

        self._manager.unassign_user_from_project(user, project)
        LOG.i(
            "User %s unassigned user %s from project %s",
            request.authenticated_user_id,
            user.identifier,
            project.identifier,
        )


class ProjectDeleteHandler(ActionHandler):
    """Handles remote project deletion requests."""

    def __init__(self, manager: ProjectManager):
        super().__init__(None)
        self._manager = manager

    def handle(self, request: ClientRequest, response: ServerResponse):
        project = request.project
        if project is None or not project.identifier:
            response.add_error(
                ResponseMessage(
                    code=ResponseCode.INCOMPLETE_REQUEST,
                    text="No managed project identifier provided.",
                )
            )
            return

        self._manager.delete_project(project)
        LOG.i(
            "User %s deleted project %s",
            request.authenticated_user_id,
            project.identifier,
        )
