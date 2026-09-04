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
"""CLI command registry."""

from raven.fathom.client.cli.arguments import ArgumentsCLI
from raven.fathom.client.cli.command import Command
from raven.fathom.client.cli.deploy import DeployCommand
from raven.fathom.client.cli.manage import ManageCommand
from raven.fathom.client.cli.setup import SetupCommand
from raven.fathom.client.logging import Logger


LOG = Logger.get()


def command_with_args(args: ArgumentsCLI) -> Command:
    """Creates a concrete Command from parsed CLI arguments.

    Args:
        args: An `ArgumentsCLI` object.

    Returns:
        A concrete `Command` instance that can be executed.

    Raises:
        ValueError: If the command name is invalid.
    """
    name = args.command
    if name == "deploy":
        return DeployCommand(args)
    if name == "manage":
        return ManageCommand(args)
    if name == "setup":
        return SetupCommand(args)

    LOG.e("Invalid command: '%s'", name)
    raise ValueError(f"Invalid command '{name}'")
