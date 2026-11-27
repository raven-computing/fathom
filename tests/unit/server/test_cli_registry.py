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

from typing import cast

from raven.fathom.server.cli import AppArgs
from raven.fathom.server.cli import AppCommand
from raven.fathom.server.cli import create_command
from raven.fathom.server.cli.reset import ResetSharedSecretCommand
from raven.fathom.server.cli.reset import ResetUserCommand
from raven.fathom.server.cli.serve import ServeCommand
from raven.fathom.server.cli.setup import SetupCommand

from tests.unit import TestCase


class TestServerCommandRegistry(TestCase):
    """Unit tests for the `create_command()` function."""

    def test_registry_works_for_no_command(self):
        command = create_command(AppArgs())
        self.assertIsInstance(command, ServeCommand)

    def test_registry_works_for_serve_command(self):
        command = create_command(AppArgs(command=AppCommand.SERVE))
        self.assertIsInstance(command, ServeCommand)

    def test_registry_works_for_setup_command(self):
        command = create_command(AppArgs(command=AppCommand.SETUP))
        self.assertIsInstance(command, SetupCommand)

    def test_registry_works_for_reset_user_command(self):
        command = create_command(
            AppArgs(command=AppCommand.RESET, reset_subject=AppCommand.USER)
        )
        self.assertIsInstance(command, ResetUserCommand)

    def test_registry_works_for_reset_shared_secret_command(self):
        command = create_command(
            AppArgs(
                command=AppCommand.RESET,
                reset_subject=AppCommand.SHARED_SECRET,
            )
        )
        self.assertIsInstance(command, ResetSharedSecretCommand)

    def test_registry_rejects_invalid_command(self):
        with self.assertRaises(ValueError) as raised:
            create_command(AppArgs(command=cast(AppCommand, "invalid")))

        self.assertIn("Invalid command 'invalid'", str(raised.exception))

    def test_registry_rejects_invalid_reset_subject(self):
        with self.assertRaises(ValueError) as raised:
            create_command(
                AppArgs(
                    command=AppCommand.RESET,
                    reset_subject=cast(AppCommand, "oops"),
                )
            )

        self.assertIn("Invalid reset subject 'oops'", str(raised.exception))


if __name__ == "__main__":
    TestCase.run_tests()
