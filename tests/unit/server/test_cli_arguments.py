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
"""Unit tests for server CLI argument parsing."""

from raven.fathom.server.cli.arguments import AppArgs, parse_args

from tests.unit import TestCase


class TestServerArgumentsCLI(TestCase):
    """Unit tests for the server CLI parser."""

    def test_setup_command_is_recognized(self):
        args = parse_args(["fathom-server", "setup"])

        self.assertIsInstance(args, AppArgs)
        self.assertEqual(args.command, "setup")

    def test_user_create_arguments_are_parsed(self):
        args = parse_args([
            "fathom-server", "user", "create", "alpha",
            "--name", "Alpha User",
        ])

        self.assertEqual(args.command, "user")
        self.assertEqual(args.user_command, "create")
        self.assertEqual(args.user_identifier, "alpha")
        self.assertEqual(args.user_name, "Alpha User")
        self.assertFalse(args.user_is_admin)

    def test_user_create_admin_flag_is_parsed(self):
        args = parse_args([
            "fathom-server", "user", "create", "alpha",
            "--admin",
        ])

        self.assertEqual(args.user_command, "create")
        self.assertTrue(args.user_is_admin)

    def test_user_list_command_is_parsed(self):
        args = parse_args(["fathom-server", "user", "list"])

        self.assertEqual(args.command, "user")
        self.assertEqual(args.user_command, "list")
        self.assertEqual(args.user_identifier, "")

    def test_user_delete_command_is_parsed(self):
        args = parse_args(["fathom-server", "user", "delete", "alpha"])

        self.assertEqual(args.command, "user")
        self.assertEqual(args.user_command, "delete")
        self.assertEqual(args.user_identifier, "alpha")

    def test_project_create_arguments_are_parsed(self):
        args = parse_args([
            "fathom-server", "project", "create", "alpha-project",
            "--name", "Alpha Project",
            "--description", "Primary project",
        ])

        self.assertEqual(args.command, "project")
        self.assertEqual(args.project_command, "create")
        self.assertEqual(args.project_identifier, "alpha-project")
        self.assertEqual(args.project_name, "Alpha Project")
        self.assertEqual(args.project_description, "Primary project")

    def test_project_list_command_is_parsed(self):
        args = parse_args(["fathom-server", "project", "list"])

        self.assertEqual(args.command, "project")
        self.assertEqual(args.project_command, "list")
        self.assertEqual(args.project_identifier, "")

    def test_project_delete_command_is_parsed(self):
        args = parse_args([
            "fathom-server", "project", "delete", "alpha-project"
        ])

        self.assertEqual(args.command, "project")
        self.assertEqual(args.project_command, "delete")
        self.assertEqual(args.project_identifier, "alpha-project")


if __name__ == "__main__":
    TestCase.run_tests()
