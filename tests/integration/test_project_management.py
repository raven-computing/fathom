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
"""Integration tests for server-side project management."""

from raven.fathom.base import Project
from raven.fathom.server.dao import DataAccess
from raven.fathom.server.project_management import ProjectManager

from tests.integration import DatabaseIntegrationTestCase


class TestProjectManagement(DatabaseIntegrationTestCase):
    """Tests project management operations against the database."""

    def setUp(self):
        super().setUp()
        self.db = DataAccess.instance()

    def test_can_create_project(self):
        project = Project(
            identifier="test-project-3",
            name="Test Project 3",
            description="A Project for Testing Purposes (3).",
        )
        ProjectManager().create_project(project)

        stored_project = self.db.projects().find_by_identifier(
            "test-project-3"
        )
        self.assertIsNotNone(stored_project)
        assert stored_project is not None
        self.assertEqual(stored_project.name, "Test Project 3")
        self.assertEqual(
            stored_project.description,
            "A Project for Testing Purposes (3)."
        )

    def test_list_projects_returns_registered_projects(self):
        ProjectManager().create_project(
            Project(
                identifier="test-project-3",
                name="Test Project 3",
                description="A Project for Testing Purposes (3).",
            )
        )

        projects = ProjectManager().list_projects()

        self.assertEqual(
            [project.identifier for project in projects],
            ["test-project-1", "test-project-2", "test-project-3"]
        )

    def test_delete_project_removes_record(self):
        ProjectManager().delete_project(Project(identifier="test-project-1"))

        self.assertIsNone(
            self.db.projects().find_by_identifier("test-project-1")
        )


if __name__ == "__main__":
    DatabaseIntegrationTestCase.run_tests()
