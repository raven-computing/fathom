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
"""Unit tests for the command handling infrastructure."""

from typing import cast

from raven.fathom.client.cli.command import ClientCommand, run
from raven.fathom.client.cli.arguments import AppCommand
from raven.fathom.client.cli.arguments import ArgumentsCLI
from raven.fathom.client.cli.registry import create_command
from raven.fathom.client.cli.deploy import DeployCommand
from raven.fathom.client.cli.manage import ManageCommand
from raven.fathom.client.cli.setup import SetupCommand
from raven.fathom.client.cli.status import ExitStatus

from tests.unit import TestCase


class TestCommand(TestCase):
    """Unit tests for the `run()` function that handles `Command` objects."""

    def test_run_returns_gracefully_when_no_command_is_provided(self):
        command = None
        status = run(command) # type: ignore
        self.assertEqual(ExitStatus.NO_COMMAND_PROVIDED, status)

    def test_run_ret_error_when_command_does_not_return_exit_status_type(self):
        class _MyCommand(ClientCommand):
            def execute(self):
                return 42

        command = _MyCommand(ArgumentsCLI())
        status = run(command)
        self.assertEqual(ExitStatus.INTERNAL_ERROR, status)

    def test_run_captures_keyboard_interrupt_and_calls_cancel(self):
        class _MyCommand(ClientCommand):
            def __init__(self, args):
                super().__init__(args)
                self.cancel_called = False
            def execute(self):
                raise KeyboardInterrupt("Test")
            def cancel(self):
                self.cancel_called = True

        command = _MyCommand(ArgumentsCLI())
        status = run(command)
        self.assertEqual(ExitStatus.CANCELLED, status)
        self.assertTrue(command.cancel_called)

    def test_run_catches_bare_exception(self):
        class _MyCommand(ClientCommand):
            def __init__(self, args):
                super().__init__(args)
                self.cancel_called = False
            def execute(self):
                raise ValueError("Test")
            def cancel(self):
                self.cancel_called = True

        command = _MyCommand(ArgumentsCLI())
        status = run(command)
        self.assertEqual(ExitStatus.INTERNAL_ERROR, status)
        self.assertFalse(command.cancel_called)


class TestCommandRegistry(TestCase):
    """Unit tests for the `command_with_args()` function."""

    def test_registry_works_for_known_command(self):
        args = ArgumentsCLI(command=AppCommand.DEPLOY, user="sentinel")
        command_obj = create_command(args)
        self.assertIsNotNone(command_obj)
        assert command_obj is not None
        self.assertIsInstance(command_obj, DeployCommand)
        self.assertEqual("sentinel", command_obj.args.user)

    def test_registry_works_for_manage_command(self):
        args = ArgumentsCLI(
            command=AppCommand.MANAGE,
            manage_subject=AppCommand.USER,
            manage_command=AppCommand.LIST,
        )
        command_obj = create_command(args)
        self.assertIsInstance(command_obj, ManageCommand)

    def test_registry_works_for_setup_command(self):
        args = ArgumentsCLI(
            command=AppCommand.SETUP,
            setup_subject=AppCommand.USER,
            setup_user_identifier="user2",
        )
        command_obj = create_command(args)
        self.assertIsInstance(command_obj, SetupCommand)

    def test_registry_works_for_setup_config_command(self):
        args = ArgumentsCLI(
            command=AppCommand.SETUP,
            setup_subject=AppCommand.CONFIG,
            setup_command=AppCommand.USER,
        )
        command_obj = create_command(args)
        self.assertIsInstance(command_obj, SetupCommand)

    def test_registry_rejects_unknown_command_and_raises_exception(self):
        args = ArgumentsCLI(command=cast(AppCommand, "invalid_command"))
        with self.assertRaises(ValueError) as raised:
            create_command(args)

        self.assertIn(
            "Invalid command 'invalid_command'",
            str(raised.exception)
        )


if __name__ == "__main__":
    TestCase.run_tests()
