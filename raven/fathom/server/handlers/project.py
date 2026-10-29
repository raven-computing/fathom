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


class ProjectCreateHandler(ActionHandler):
    """Handles remote project creation requests."""

    def __init__(self, authorizer: UserAuthorizer, manager: ProjectManager):
        super().__init__(authorizer)
        self._manager = manager

    @require_admin_privileges
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

        try:
            self._manager.create_project(project)
        except ProjectManagementException as ex:
            response.add_error(
                ResponseMessage(
                    code=ResponseCode.INCOMPLETE_REQUEST,
                    text=str(ex),
                )
            )
            LOG.i(
                "User %s requested to create a new project %s "
                "but the operation has failed: %s",
                request.authenticated_user_id,
                project.identifier,
                str(ex),
            )
            return

        LOG.i(
            "User %s created new project %s",
            request.authenticated_user_id,
            project.identifier,
        )
        response.projects = [project]


class ProjectListHandler(ActionHandler):
    """Handles remote project listing requests."""

    def __init__(self, authorizer: UserAuthorizer, manager: ProjectManager):
        super().__init__(authorizer)
        self._manager = manager

    @require_admin_privileges
    def handle(self, request: ClientRequest, response: ServerResponse):
        try:
            response.projects = self._manager.list_projects()
        except ProjectManagementException as ex:
            response.add_error(
                ResponseMessage(
                    code=ResponseCode.INTERNAL_ERROR,
                    text=str(ex),
                )
            )
            LOG.i(
                "User %s requested to view a list of all available projects "
                "but the operation has failed: %s",
                request.authenticated_user_id,
                str(ex),
            )
            return

        LOG.i(
            "User %s requested to view a list of all available projects",
            request.authenticated_user_id,
        )


class ProjectUserListHandler(ActionHandler):
    """Handles remote project-user listing requests."""

    def __init__(self, authorizer: UserAuthorizer, manager: ProjectManager):
        super().__init__(authorizer)
        self._manager = manager

    @require_admin_privileges
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


        try:
            response.users = self._manager.list_project_users(project)
        except ProjectNotFoundException as ex:
            response.add_error(
                ResponseMessage(
                    code=ResponseCode.NOT_FOUND,
                    text=str(ex),
                )
            )
            LOG.i(
                "User %s requested to view a list of users assigned "
                "to project %s but no such project exists",
                request.authenticated_user_id,
                project.identifier,
            )
            return
        except ProjectManagementException as ex:
            response.add_error(
                ResponseMessage(
                    code=ResponseCode.INTERNAL_ERROR,
                    text=str(ex),
                )
            )
            LOG.i(
                "User %s requested to view a list of users assigned "
                "to project %s but the operation has failed: %s",
                request.authenticated_user_id,
                project.identifier,
                str(ex),
            )
            return

        LOG.i(
            "User %s requested to view a list of users assigned to project %s",
            request.authenticated_user_id,
            project.identifier,
        )


class ProjectUserAssignHandler(ActionHandler):
    """Handles remote project-user assignment requests."""

    def __init__(self, authorizer: UserAuthorizer, manager: ProjectManager):
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

        project = request.project
        if project is None or not project.identifier:
            response.add_error(
                ResponseMessage(
                    code=ResponseCode.INCOMPLETE_REQUEST,
                    text="No managed project identifier provided.",
                )
            )
            return

        try:
            self._manager.assign_user_to_project(user, project)
        except ProjectNotFoundException as ex:
            response.add_error(
                ResponseMessage(
                    code=ResponseCode.NOT_FOUND,
                    text=str(ex),
                )
            )
            LOG.i(
                "User %s requested to assign user %s to project %s "
                "but no such project exists",
                request.authenticated_user_id,
                user.identifier,
                project.identifier,
            )
            return
        except ProjectManagementException as ex:
            response.add_error(
                ResponseMessage(
                    code=ResponseCode.INTERNAL_ERROR,
                    text=str(ex),
                )
            )
            LOG.i(
                "User %s requested to assign user %s to project %s "
                "but the operation has failed: %s",
                request.authenticated_user_id,
                user.identifier,
                project.identifier,
                str(ex),
            )
            return

        LOG.i(
            "User %s assigned user %s to project %s",
            request.authenticated_user_id,
            user.identifier,
            project.identifier,
        )


class ProjectUserUnassignHandler(ActionHandler):
    """Handles remote project-user unassignment requests."""

    def __init__(self, authorizer: UserAuthorizer, manager: ProjectManager):
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

        project = request.project
        if project is None or not project.identifier:
            response.add_error(
                ResponseMessage(
                    code=ResponseCode.INCOMPLETE_REQUEST,
                    text="No managed project identifier provided.",
                )
            )
            return

        try:
            self._manager.unassign_user_from_project(user, project)
        except ProjectNotFoundException as ex:
            response.add_error(
                ResponseMessage(
                    code=ResponseCode.NOT_FOUND,
                    text=str(ex),
                )
            )
            LOG.i(
                "User %s requested to unassign user %s from project %s "
                "but no such project exists",
                request.authenticated_user_id,
                user.identifier,
                project.identifier,
            )
            return
        except ProjectManagementException as ex:
            response.add_error(
                ResponseMessage(
                    code=ResponseCode.INTERNAL_ERROR,
                    text=str(ex),
                )
            )
            LOG.i(
                "User %s requested to unassign user %s from project %s "
                "but the operation has failed: %s",
                request.authenticated_user_id,
                user.identifier,
                project.identifier,
                str(ex),
            )
            return

        LOG.i(
            "User %s unassigned user %s from project %s",
            request.authenticated_user_id,
            user.identifier,
            project.identifier,
        )


class ProjectDeleteHandler(ActionHandler):
    """Handles remote project deletion requests."""

    def __init__(self, authorizer: UserAuthorizer, manager: ProjectManager):
        super().__init__(authorizer)
        self._manager = manager

    @require_admin_privileges
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

        try:
            self._manager.delete_project(project)
        except ProjectNotFoundException as ex:
            response.add_error(
                ResponseMessage(
                    code=ResponseCode.NOT_FOUND,
                    text=str(ex),
                )
            )
            LOG.i(
                "User %s requested the deletion of project %s "
                "but no such project exists",
                request.authenticated_user_id,
                project.identifier,
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
                "User %s requested the deletion of project %s "
                "but an internal error has occurred: %s",
                request.authenticated_user_id,
                project.identifier,
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
                "User %s requested the deletion of project %s "
                "but the operation was rejected: %s",
                request.authenticated_user_id,
                project.identifier,
                str(ex),
            )
            return

        LOG.i(
            "User %s deleted project %s",
            request.authenticated_user_id,
            project.identifier,
        )
