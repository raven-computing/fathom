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
from raven.fathom.server.cli.command import require_privileges
from raven.fathom.server.cli.command import ServerCommand
from raven.fathom.server.logging import Logger
from raven.fathom.server.security import UserAuthenticator
from raven.fathom.server.user_management import UserManager


LOG = Logger.get()


class UserCreateCommand(ServerCommand):
    """Implementation of `user create`."""

    @require_privileges
    def execute(self) -> int:
        manager = UserManager(UserAuthenticator())
        user = User(
            identifier=self.args.user_identifier,
            name=self.args.user_name,
            is_admin=self.args.user_is_admin,
            state=UserState.ONBOARDING,
        )
        manager.create_user(user)
        role = "admin" if user.is_admin else "user"
        LOG.i(
            "Created user '%s' (%s, %s).",
            user.identifier,
            role,
            user.state,
        )
        return 0


class UserListCommand(ServerCommand):
    """Implementation of `user list`."""

    @require_privileges
    def execute(self) -> int:
        manager = UserManager(UserAuthenticator())
        for user in manager.list_users():
            role = manager.get_user_role(user.identifier).value
            LOG.i(
                "User: '%s'\tName: '%s'\tRole: '%s'\tState: '%s'",
                user.identifier,
                user.name,
                role,
                user.state,
            )
        return 0


class UserDeleteCommand(ServerCommand):
    """Implementation of `user delete`."""

    @require_privileges
    def execute(self) -> int:
        manager = UserManager(UserAuthenticator())
        manager.delete_user(User(identifier=self.args.user_identifier))
        LOG.i("Deleted user '%s'.", self.args.user_identifier)
        return 0
