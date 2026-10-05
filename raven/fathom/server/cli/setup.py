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
"""CLI command handling for setup actions."""

from raven.fathom.base import InputPrompt, User
from raven.fathom.server.cli.command import require_database
from raven.fathom.server.cli.command import ServerCommand
from raven.fathom.server.logging import Logger
from raven.fathom.server.models import Settings
from raven.fathom.server.security import UserAuthenticator
from raven.fathom.server.user_management import SYSTEM_USER_IDENTIFIER
from raven.fathom.server.user_management import UserManager


LOG = Logger.get()


class SetupCommand(ServerCommand):
    """Implementation of the `setup` server command."""

    @require_database
    def execute(self) -> int:
        prompt = InputPrompt.instance()
        password = prompt.read("Password: ", secret=True)
        if not password:
            raise ValueError("Password must not be empty.")

        confirmation = prompt.read("Confirm password: ", secret=True)
        if password != confirmation:
            raise ValueError("Password confirmation does not match.")

        user = User(
            identifier="",
            password=password,
        )
        UserManager(UserAuthenticator()).create_system_user(user)
        Settings.create(
            organisation_name="System",
            shared_secret="whatever",
            active=True,
        )
        LOG.i("Configured system user '%s'.", SYSTEM_USER_IDENTIFIER)
        return 0
