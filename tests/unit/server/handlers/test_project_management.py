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
"""Unit tests for remote project-management handlers."""

from raven.fathom.base import ClientRequest, Interaction, ServerResponse
from raven.fathom.base import ResponseCode, User, Project
from raven.fathom.server.handlers.project import (
    ProjectHandler, ProjectCreateHandler, ProjectListHandler,
    ProjectUserListHandler, ProjectDeleteHandler, ProjectUserAssignHandler,
    ProjectUserUnassignHandler,
)
from raven.fathom.server.security import UserAuthorizer
from raven.fathom.server.domain.project import (
    ProjectManager,
    ProjectNotFoundException,
)

from tests.unit import TestCase
from tests.unit.mocks import Mock


class TestProjectManagementHandlers(TestCase):
    """Unit tests for remote project-management handlers."""

    def setUp(self):
        super().setUp()
        self.admin_authorizer = Mock(spec_set=UserAuthorizer)
        self.manager = Mock(spec_set=ProjectManager)
        self.request_user = User(identifier="admin", name="Admin User")

    def test_create_handler_rejects_non_admin(self):
        self.admin_authorizer.is_administrator.return_value = False
        request = ClientRequest(Interaction.CREATE_PROJECT)
        request.authenticated_user = self.request_user
        response = ServerResponse(Interaction.CREATE_PROJECT)

        ProjectHandler(
            self.admin_authorizer,
            ProjectCreateHandler(self.manager),
            "creation of new project",
        ).handle(request, response)

        self.assertEqual(
            response.errors[0].code,
            ResponseCode.AUTHORIZATION_DENIED,
        )
        self.manager.create_project.assert_not_called()

    def test_create_handler_creates_project(self):
        self.admin_authorizer.is_administrator.return_value = True
        request = ClientRequest(Interaction.CREATE_PROJECT)
        request.authenticated_user = self.request_user
        request.project = Project(
            identifier="proj-one",
            name="Project One",
            description="Project One Description",
        )
        response = ServerResponse(Interaction.CREATE_PROJECT)

        ProjectHandler(
            self.admin_authorizer,
            ProjectCreateHandler(self.manager),
            "creation of new project",
        ).handle(request, response)

        self.assertFalse(response.has_errors())
        assert response.projects is not None
        self.assertEqual(len(response.projects), 1)
        self.manager.create_project.assert_called_once_with(
            Project(
                identifier="proj-one",
                name="Project One",
                description="Project One Description",
            )
        )

    def test_list_handler_returns_projects(self):
        self.admin_authorizer.is_administrator.return_value = True
        self.manager.list_projects.return_value = [
            Project(identifier="proj-one", name="Project One"),
        ]
        request = ClientRequest(Interaction.LIST_PROJECTS)
        request.authenticated_user = self.request_user
        response = ServerResponse(Interaction.LIST_PROJECTS)

        ProjectHandler(
            self.admin_authorizer,
            ProjectListHandler(self.manager),
            "listing of available projects",
        ).handle(request, response)

        self.assertFalse(response.has_errors())
        self.assertEqual(
            response.projects,
            self.manager.list_projects.return_value,
        )

    def test_list_users_handler_rejects_non_admin(self):
        self.admin_authorizer.is_administrator.return_value = False
        request = ClientRequest(Interaction.LIST_PROJECT_USERS)
        request.authenticated_user = self.request_user
        request.project = Project(identifier="proj-one")
        response = ServerResponse(Interaction.LIST_PROJECT_USERS)

        ProjectHandler(
            self.admin_authorizer,
            ProjectUserListHandler(self.manager),
            "listing of assigned users to project",
        ).handle(request, response)

        self.assertEqual(
            response.errors[0].code,
            ResponseCode.AUTHORIZATION_DENIED,
        )
        self.manager.list_project_users.assert_not_called()

    def test_list_users_handler_returns_project_users(self):
        self.admin_authorizer.is_administrator.return_value = True
        self.manager.list_project_users.return_value = [
            User(identifier="user-one", name="User One"),
        ]
        request = ClientRequest(Interaction.LIST_PROJECT_USERS)
        request.authenticated_user = self.request_user
        request.project = Project(identifier="proj-one")
        response = ServerResponse(Interaction.LIST_PROJECT_USERS)

        ProjectHandler(
            self.admin_authorizer,
            ProjectUserListHandler(self.manager),
            "listing of assigned users to project",
        ).handle(request, response)

        self.assertFalse(response.has_errors())
        self.assertEqual(
            response.users,
            self.manager.list_project_users.return_value,
        )

    def test_delete_handler_reports_unknown_project(self):
        self.admin_authorizer.is_administrator.return_value = True
        self.manager.delete_project.side_effect = ProjectNotFoundException(
            "Project 'proj-one' does not exist"
        )
        request = ClientRequest(Interaction.DELETE_PROJECT)
        request.authenticated_user = self.request_user
        request.project = Project(identifier="proj-one")
        response = ServerResponse(Interaction.DELETE_PROJECT)

        ProjectHandler(
            self.admin_authorizer,
            ProjectDeleteHandler(self.manager),
            "deletion of project",
        ).handle(request, response)

        self.assertEqual(response.errors[0].code, ResponseCode.NOT_FOUND)

    def test_assign_handler_assigns_user_to_project(self):
        self.admin_authorizer.is_administrator.return_value = True
        request = ClientRequest(Interaction.ASSIGN_USER)
        request.authenticated_user = self.request_user
        request.user = User(identifier="someone")
        request.project = Project(identifier="project-1")
        response = ServerResponse(Interaction.ASSIGN_USER)

        ProjectHandler(
            self.admin_authorizer,
            ProjectUserAssignHandler(self.manager),
            "assignment of user",
        ).handle(request, response)

        self.assertFalse(response.has_errors())
        self.manager.assign_user_to_project.assert_called_once_with(
            request.user,
            request.project,
        )

    def test_unassign_handler_unassigns_user_from_project(self):
        self.admin_authorizer.is_administrator.return_value = True
        request = ClientRequest(Interaction.UNASSIGN_USER)
        request.authenticated_user = self.request_user
        request.user = User(identifier="someone")
        request.project = Project(identifier="project-1")
        response = ServerResponse(Interaction.UNASSIGN_USER)

        ProjectHandler(
            self.admin_authorizer,
            ProjectUserUnassignHandler(self.manager),
            "unassignment of user in project",
        ).handle(request, response)

        self.assertFalse(response.has_errors())
        self.manager.unassign_user_from_project.assert_called_once_with(
            request.user,
            request.project,
        )


if __name__ == "__main__":
    TestCase.run_tests()
