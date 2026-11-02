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
"""CLI command handling for user management actions."""

from raven.fathom.base import User, UserState
from raven.fathom.base import TableFormatter
from raven.fathom.server.cli.command import ServerCommand
from raven.fathom.server.cli.status import ExitStatus
from raven.fathom.server.core.logging import Logger
from raven.fathom.server.security import UserAuthenticator
from raven.fathom.server.core.user_management import UserManager


LOG = Logger.get()


class UserCreateCommand(ServerCommand):
    """Implementation of `user create`."""

    def execute(self) -> int:
        user = User(
            identifier=self.args.user_identifier,
            name=self.args.user_name,
            is_admin=self.args.user_is_admin,
            state=UserState.ONBOARDING,
        )
        LOG.d("Creating user '%s'", user.identifier)
        UserManager(UserAuthenticator()).create_user(user)
        role = "admin" if user.is_admin else "user"
        LOG.i(
            "Created user '%s' (%s, %s).",
            user.identifier,
            role,
            user.state,
        )
        return ExitStatus.SUCCESS


class UserListCommand(ServerCommand):
    """Implementation of `user list`."""

    def execute(self) -> int:
        formatter = TableFormatter().set_headers(
            "Identifier", "Name", "Role", "State"
        )
        LOG.d("Fetching user list")
        manager = UserManager(UserAuthenticator())
        users = manager.list_users()
        for user in users:
            role = manager.get_user_role(user.identifier)
            formatter.add_row(
                user.identifier,
                user.name,
                role.value,
                user.state,
            )

        LOG.i("User list:")
        self._print_table(formatter)
        return ExitStatus.SUCCESS


class UserDeleteCommand(ServerCommand):
    """Implementation of `user delete`."""

    def execute(self) -> int:
        user = User(identifier=self.args.user_identifier)
        LOG.d("Deleting user '%s'", user.identifier)
        UserManager(UserAuthenticator()).delete_user(user)
        LOG.i("Deleted user '%s'.", self.args.user_identifier)
        return ExitStatus.SUCCESS
