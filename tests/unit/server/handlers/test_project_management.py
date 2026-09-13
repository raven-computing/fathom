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
from raven.fathom.server.handlers.project_management import (
    ProjectCreateHandler, ProjectListHandler, ProjectDeleteHandler,
)
from raven.fathom.server.security import UserAuthorizer
from raven.fathom.server.project_management import ProjectManager

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
        request.user = self.request_user
        response = ServerResponse(Interaction.CREATE_PROJECT)

        ProjectCreateHandler(self.admin_authorizer, self.manager).handle(
            request, response
        )

        self.assertEqual(
            response.errors[0].code,
            ResponseCode.AUTHORIZATION_DENIED,
        )
        self.manager.create_project.assert_not_called()

    def test_create_handler_creates_project(self):
        self.admin_authorizer.is_administrator.return_value = True
        request = ClientRequest(Interaction.CREATE_PROJECT)
        request.user = self.request_user
        request.managed_project = Project(
            identifier="proj-one",
            name="Project One",
            description="Project One Description",
        )
        response = ServerResponse(Interaction.CREATE_PROJECT)

        ProjectCreateHandler(self.admin_authorizer, self.manager).handle(
            request, response
        )

        self.assertFalse(response.has_errors())
        assert response.managed_projects is not None
        self.assertEqual(len(response.managed_projects), 1)
        self.manager.create_project.assert_called_once_with(
            Project(
                identifier="proj-one",
                name="Project One",
                description="Project One Description",
            )
        )

    def test_list_handler_returns_managed_projects(self):
        self.admin_authorizer.is_administrator.return_value = True
        self.manager.list_projects.return_value = [
            Project(identifier="proj-one", name="Project One"),
        ]
        request = ClientRequest(Interaction.LIST_PROJECTS)
        request.user = self.request_user
        response = ServerResponse(Interaction.LIST_PROJECTS)

        ProjectListHandler(self.admin_authorizer, self.manager).handle(
            request, response
        )

        self.assertFalse(response.has_errors())
        self.assertEqual(
            response.managed_projects,
            self.manager.list_projects.return_value,
        )

    def test_delete_handler_reports_unknown_project(self):
        self.admin_authorizer.is_administrator.return_value = True
        self.manager.delete_project.side_effect = ValueError(
            "Project 'proj-one' does not exist"
        )
        request = ClientRequest(Interaction.DELETE_PROJECT)
        request.user = self.request_user
        request.managed_project = Project(identifier="proj-one")
        response = ServerResponse(Interaction.DELETE_PROJECT)

        ProjectDeleteHandler(self.admin_authorizer, self.manager).handle(
            request, response
        )

        self.assertEqual(response.errors[0].code, ResponseCode.NOT_FOUND)


if __name__ == "__main__":
    TestCase.run_tests()
