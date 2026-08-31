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
"""Integration tests for the data access implementation using SQLite."""

from datetime import datetime

from raven.fathom.server.dao import DataAccess
from raven.fathom.server.dao import IncoherentDatastoreStateException
from raven.fathom.server.datastore import DatabaseManager
from raven.fathom.server.models import User, Project
from raven.fathom.server.models import AuthDeployment
from raven.fathom.server.datastore._data_access import DataAccessRDBMS
from raven.fathom.server.datastore._sqlite import DatabaseSQLite

from tests.integration import DatabaseIntegrationTestCase


class TestDatabaseSQLite(DatabaseIntegrationTestCase):
    """Tests the `DataAccess` implementation using SQLite."""

    def setUp(self):
        super().setUp()
        self.db = DataAccess.instance()
        self.assertIsInstance(self.db, DataAccessRDBMS)
        sqlite_db = DatabaseManager().get_database()
        self.assertIsInstance(sqlite_db, DatabaseSQLite)
        self.assertEqual("SQLite", sqlite_db.type_name())

    ###########################################################################
    #                                                                         #
    #                              UserDAO Tests                              #
    #                                                                         #
    ###########################################################################

    def test_query_can_find_user_by_identifier(self):
        user = self.db.users().find_by_identifier("test-user-1")
        self.assertIsNotNone(user)
        assert user is not None
        self.assertEqual(user.name, "Test User 1")
        self.assertEqual(user.password, "123456")

    def test_query_to_find_user_with_unknown_identifier_returns_none(self):
        user = self.db.users().find_by_identifier("this-user-does-not-exist")
        self.assertIsNone(user)

    def test_query_can_find_user_permission_for_user(self):
        user = self.db.users().find_by_identifier("test-user-1")
        self.assertIsNotNone(user)
        assert user is not None
        permission = self.db.users().find_permission(user)
        self.assertIsNotNone(permission)
        self.assertEqual(permission.user, user)
        self.assertTrue(permission.allow_overwrite)

    def test_query_to_find_user_permission_for_unknown_user_raises_ex(self):
        user = User.create(
            identifier="test-user-2",
            name="Test User 2",
            password="567890",
        )
        with self.assertRaises(IncoherentDatastoreStateException) as raised:
            self.db.users().find_permission(user)

        self.assertIn(
            "Missing <Model: UserPermission> record "
            "associated with <Model: User> record",
            str(raised.exception)
        )

    def test_query_can_find_deployment_authorization_by_token(self):
        auth = self.db.users().find_deployment_authorization_by_token(
            "abcdefghijklmnopqrstuvwxyz0123456789"
        )
        self.assertIsNotNone(auth)
        assert auth is not None
        self.assertEqual(auth.token, "abcdefghijklmnopqrstuvwxyz0123456789")

    def test_query_find_deployment_auth_by_invalid_token_returns_none(self):
        auth = self.db.users().find_deployment_authorization_by_token(
            "this-token-does-not-exist"
        )
        self.assertIsNone(auth)

    def test_can_persist_deployment_authorization(self):
        user = self.db.users().find_by_identifier("test-user-1")
        project = self.db.projects().find_by_identifier("test-project-1")
        self.assertIsNotNone(project)
        assert project is not None
        auth = AuthDeployment(
            token="abcdef123456",
            expiration_time=datetime(2999, 12, 31),
            user=user,
            project=project,
            project_version=project.latest_version,
            allow_overwrite=False,
        )
        self.db.users().create(auth)

        persisted = self.db.users().find_deployment_authorization_by_token(
            "abcdef123456"
        )
        self.assertEqual(auth, persisted)


    ###########################################################################
    #                                                                         #
    #                             ProjectDAO Tests                            #
    #                                                                         #
    ###########################################################################


    def test_query_can_find_project_by_identifier(self):
        project = self.db.projects().find_by_identifier("test-project-1")
        self.assertIsNotNone(project)
        assert project is not None
        self.assertEqual(project.name, "Test Project 1")
        self.assertEqual(project.latest_version, "1.0.0")
        self.assertTrue(project.is_published)

    def test_query_to_find_project_with_unknown_identifier_returns_none(self):
        project = self.db.projects().find_by_identifier(
            "this-project-does-not-exist"
        )
        self.assertIsNone(project)

    def test_query_can_find_all_projects_assigned_to_user(self):
        user = self.db.users().find_by_identifier("test-user-1")
        project_1 = self.db.projects().find_by_identifier("test-project-1")
        self.assertIsNotNone(user)
        assert user is not None
        self.assertIsNotNone(project_1)
        assert project_1 is not None
        # Test with one project assigned
        assigned_projects = self.db.projects().find_all_assigned_to_user(user)
        self.assertEqual(len(assigned_projects), 1)
        self.assertIsInstance(assigned_projects[0], Project)
        self.assertEqual(assigned_projects[0].identifier, project_1.identifier)

        # Test with more than one project assigned
        project_2 = self.db.projects().find_by_identifier("test-project-2")
        self.assertIsNotNone(project_2)
        assert project_2 is not None
        self.db.projects().assign_user_to_project(user, project_2)
        assigned_projects = self.db.projects().find_all_assigned_to_user(user)
        self.assertEqual(len(assigned_projects), 2)
        assigned_projects.sort(key=lambda rec: rec.id) # type: ignore
        self.assertEqual(assigned_projects[0].identifier, project_1.identifier)
        self.assertEqual(assigned_projects[1].identifier, project_2.identifier)

    def test_query_finds_empty_list_for_user_with_no_assigned_projects(self):
        user = User.create(
            identifier="test-user-no-projects",
            name="Test User No Projects",
            password="no-projects",
        )
        assigned_projects = self.db.projects().find_all_assigned_to_user(user)
        self.assertIsInstance(assigned_projects, list)
        self.assertEqual(len(assigned_projects), 0)

    def test_persisted_deployment_authorization_has_correct_fields(self):
        user = self.db.users().find_by_identifier("test-user-1")
        project = self.db.projects().find_by_identifier("test-project-1")
        expiry = datetime(2999, 6, 15)
        auth = AuthDeployment(
            token="unique-roundtrip-token",
            expiration_time=expiry,
            user=user,
            project=project,
            project_version="1.0.0",
            allow_overwrite=True,
        )
        self.db.users().create(auth)

        persisted = self.db.users().find_deployment_authorization_by_token(
            "unique-roundtrip-token"
        )
        self.assertIsNotNone(persisted)
        assert persisted is not None
        self.assertEqual(persisted.token, "unique-roundtrip-token")
        self.assertEqual(persisted.user.identifier, "test-user-1")
        self.assertEqual(persisted.project.identifier, "test-project-1")
        self.assertEqual(persisted.project_version, "1.0.0")
        self.assertTrue(persisted.allow_overwrite)

    def test_query_can_find_project_description(self):
        project = self.db.projects().find_by_identifier("test-project-1")
        self.assertIsNotNone(project)
        assert project is not None
        self.assertEqual(
            project.description,
            "A Project for Testing Purposes (1)."
        )

    def test_query_can_find_second_project_by_identifier(self):
        project = self.db.projects().find_by_identifier("test-project-2")
        self.assertIsNotNone(project)
        assert project is not None
        self.assertEqual(project.name, "Test Project 2")
        self.assertEqual(project.latest_version, "2.3.4")
        self.assertTrue(project.is_published)


if __name__ == "__main__":
    DatabaseIntegrationTestCase.run_tests()
