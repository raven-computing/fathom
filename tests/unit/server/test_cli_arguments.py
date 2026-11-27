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

from raven.fathom.server.cli.arguments import AppArgs, AppCommand, parse_args

from tests.unit import TestCase


class TestServerAppArgs(TestCase):
    """Unit tests for the server CLI parser."""

    def test_setup_command_is_recognized(self):
        args = parse_args(["fathom-server", "setup"])

        self.assertIsInstance(args, AppArgs)
        self.assertEqual(args.command, "setup")

    def test_serve_command_is_recognized(self):
        args = parse_args(["fathom-server", "serve"])

        self.assertIsInstance(args, AppArgs)
        self.assertEqual(args.command, "serve")

    def test_no_command_defaults_to_serve(self):
        args = parse_args(["fathom-server"])

        self.assertIsInstance(args, AppArgs)
        self.assertEqual(args.command, AppCommand.SERVE)

    def test_external_config_file_is_recognized(self):
        args = parse_args([
            "fathom-server",
            "--config-file",
            "/etc/fathom-server/fathom.cfg",
            "serve",
        ])

        self.assertEqual(
            args.config_file,
            "/etc/fathom-server/fathom.cfg",
        )

    def test_reset_user_command_is_recognized(self):
        args = parse_args(["fathom-server", "reset", "user", "alice"])

        self.assertEqual(args.command, AppCommand.RESET)
        self.assertEqual(args.reset_subject, AppCommand.USER)
        self.assertEqual(args.reset_user_identifier, "alice")

    def test_reset_shared_secret_command_is_recognized(self):
        args = parse_args(["fathom-server", "reset", "shared-secret"])

        self.assertEqual(args.command, AppCommand.RESET)
        self.assertEqual(args.reset_subject, AppCommand.SHARED_SECRET)
        self.assertEqual(args.reset_user_identifier, "")


if __name__ == "__main__":
    TestCase.run_tests()
