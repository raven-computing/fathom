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
"""Unit tests for CLI argument parsing."""

from raven.fathom.client.cli.arguments import parse_args, ArgumentsCLI

from tests.unit import TestCase


class TestArgumentsCLI(TestCase):
    """Unit tests for the `parse_args` function."""

    def test_verbose_flag_is_false_by_default(self):
        args = parse_args(["fathom", "deploy"])
        self.assertIsInstance(args, ArgumentsCLI)
        self.assertFalse(args.verbose)

    def test_debug_flag_is_false_by_default(self):
        args = parse_args(["fathom", "deploy"])
        self.assertIsInstance(args, ArgumentsCLI)
        self.assertFalse(args.debug)

    def test_quiet_flag_is_false_by_default(self):
        args = parse_args(["fathom", "deploy"])
        self.assertIsInstance(args, ArgumentsCLI)
        self.assertFalse(args.quiet)

    def test_verbose_flag_is_set_when_provided(self):
        args = parse_args(["fathom", "--verbose", "deploy"])
        self.assertIsInstance(args, ArgumentsCLI)
        self.assertTrue(args.verbose)

    def test_debug_flag_is_set_when_provided(self):
        args = parse_args(["fathom", "--debug", "deploy"])
        self.assertIsInstance(args, ArgumentsCLI)
        self.assertTrue(args.debug)

    def test_quiet_flag_is_set_when_provided(self):
        args = parse_args(["fathom", "--quiet", "deploy"])
        self.assertIsInstance(args, ArgumentsCLI)
        self.assertTrue(args.quiet)

    def test_user_argument_is_empty_string_by_default(self):
        args = parse_args(["fathom", "deploy"])
        self.assertIsInstance(args, ArgumentsCLI)
        self.assertEqual(args.user, "")

    def test_password_argument_is_empty_string_by_default(self):
        args = parse_args(["fathom", "deploy"])
        self.assertIsInstance(args, ArgumentsCLI)
        self.assertEqual(args.password, "")

    def test_server_argument_is_empty_string_by_default(self):
        args = parse_args(["fathom", "deploy"])
        self.assertIsInstance(args, ArgumentsCLI)
        self.assertEqual(args.server, "")

    def test_project_directory_argument_is_empty_string_by_default(self):
        args = parse_args(["fathom", "deploy"])
        self.assertIsInstance(args, ArgumentsCLI)
        self.assertEqual(args.project_directory, "")

    def test_user_argument_stores_provided_value(self):
        args = parse_args(["fathom", "--user", "testuser", "deploy"])
        self.assertIsInstance(args, ArgumentsCLI)
        self.assertEqual(args.user, "testuser")

    def test_password_argument_stores_provided_value(self):
        args = parse_args(["fathom", "--password", "testpass", "deploy"])
        self.assertIsInstance(args, ArgumentsCLI)
        self.assertEqual(args.password, "testpass")

    def test_server_argument_stores_provided_value(self):
        args = parse_args(
            ["fathom", "--server", "https://example.com", "deploy"]
        )
        self.assertIsInstance(args, ArgumentsCLI)
        self.assertEqual(args.server, "https://example.com")

    def test_project_directory_argument_stores_provided_value(self):
        args = parse_args(
            ["fathom", "deploy", "--project-directory", "/my/project"]
        )
        self.assertIsInstance(args, ArgumentsCLI)
        self.assertEqual(args.project_directory, "/my/project")

    def test_deploy_command_is_recognized(self):
        args = parse_args(["fathom", "deploy"])
        self.assertIsInstance(args, ArgumentsCLI)
        self.assertEqual(args.command, "deploy")

    def test_combined_flags_and_arguments_are_parsed_correctly(self):
        args = parse_args(
            ["fathom", "--verbose",
             "--user", "alice", "--password", "secret",
             "deploy"
            ],
        )
        self.assertIsInstance(args, ArgumentsCLI)
        self.assertTrue(args.verbose)
        self.assertEqual(args.user, "alice")
        self.assertEqual(args.password, "secret")
        self.assertEqual(args.command, "deploy")


if __name__ == "__main__":
    TestCase.run_tests()
