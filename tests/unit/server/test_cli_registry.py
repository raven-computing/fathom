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
"""Unit tests for the server command registry."""

from raven.fathom.server.cli import AppArgs
from raven.fathom.server.cli import command_with_args
from raven.fathom.server.cli.run import RunServerCommand
from raven.fathom.server.cli.setup import SetupCommand
from raven.fathom.server.cli.user import UserCreateCommand
from raven.fathom.server.cli.user import UserDeleteCommand
from raven.fathom.server.cli.user import UserListCommand
from raven.fathom.server.cli.project import ProjectCreateCommand
from raven.fathom.server.cli.project import ProjectDeleteCommand
from raven.fathom.server.cli.project import ProjectListCommand

from tests.unit import TestCase


class TestServerCommandRegistry(TestCase):
    """Unit tests for the `command_with_args()` function."""

    def test_registry_works_for_no_command(self):
        command = command_with_args(AppArgs())
        self.assertIsInstance(command, RunServerCommand)

    def test_registry_works_for_setup_command(self):
        command = command_with_args(AppArgs(command="setup"))
        self.assertIsInstance(command, SetupCommand)

    def test_registry_works_for_user_create_command(self):
        command = command_with_args(
            AppArgs(command="user", user_command="create")
        )
        self.assertIsInstance(command, UserCreateCommand)

    def test_registry_works_for_user_list_command(self):
        command = command_with_args(
            AppArgs(command="user", user_command="list")
        )
        self.assertIsInstance(command, UserListCommand)

    def test_registry_works_for_user_delete_command(self):
        command = command_with_args(
            AppArgs(command="user", user_command="delete")
        )
        self.assertIsInstance(command, UserDeleteCommand)

    def test_registry_works_for_project_create_command(self):
        command = command_with_args(
            AppArgs(command="project", project_command="create")
        )
        self.assertIsInstance(command, ProjectCreateCommand)

    def test_registry_works_for_project_list_command(self):
        command = command_with_args(
            AppArgs(command="project", project_command="list")
        )
        self.assertIsInstance(command, ProjectListCommand)

    def test_registry_works_for_project_delete_command(self):
        command = command_with_args(
            AppArgs(command="project", project_command="delete")
        )
        self.assertIsInstance(command, ProjectDeleteCommand)

    def test_registry_rejects_invalid_command(self):
        with self.assertRaises(ValueError) as raised:
            command_with_args(AppArgs(command="invalid"))

        self.assertIn("Invalid command 'invalid'", str(raised.exception))

    def test_registry_rejects_invalid_user_subcommand(self):
        with self.assertRaises(ValueError) as raised:
            command_with_args(AppArgs(command="user", user_command="oops"))

        self.assertIn("Invalid user command 'oops'", str(raised.exception))

    def test_registry_rejects_invalid_project_subcommand(self):
        with self.assertRaises(ValueError) as raised:
            command_with_args(
                AppArgs(command="project", project_command="oops")
            )

        self.assertIn("Invalid project command 'oops'", str(raised.exception))


if __name__ == "__main__":
    TestCase.run_tests()
