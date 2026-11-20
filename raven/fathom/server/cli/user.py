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
from raven.fathom.server.cli.arguments import AppArgs
from raven.fathom.server.cli.command import ServerCommand
from raven.fathom.server.cli.status import ExitStatus
from raven.fathom.server.core.logging import Logger
from raven.fathom.server.core.user_management import (
    InvalidUserRequestException,
    UserManager,
    UserPermissionKey,
)


LOG = Logger.get()


def _create_permission_key(value: str) -> UserPermissionKey:
    try:
        return UserPermissionKey(value)
    except ValueError as ex:
        raise InvalidUserRequestException(
            f"Invalid permission key: {value}"
        ) from ex


class UserCreateCommand(ServerCommand):
    """Implementation of `user create`."""

    def __init__(self, args: AppArgs, manager: UserManager):
        super().__init__(args)
        self._manager = manager

    def execute(self) -> int:
        user = User(
            identifier=self.args.user_identifier,
            name=self.args.user_name,
            is_admin=self.args.user_is_admin,
            state=UserState.ONBOARDING,
        )
        LOG.d("Creating user '%s'", user.identifier)
        self._manager.create_user(user)
        role_msg = (
            "with admin privileges"
            if user.is_admin
            else "with regular user privileges"
        )
        LOG.i(
            "Created user %s %s",
            user.identifier,
            role_msg,
        )
        if user.state == UserState.ONBOARDING:
            LOG.i(
                "User %s can now be onboarded "
                "via the client application",
                user.identifier,
            )

        return ExitStatus.SUCCESS


class UserListCommand(ServerCommand):
    """Implementation of `user list`."""

    def __init__(self, args: AppArgs, manager: UserManager):
        super().__init__(args)
        self._manager = manager

    def execute(self) -> int:
        formatter = TableFormatter().set_headers(
            "Identifier", "Name", "Role", "State"
        )
        LOG.d("Fetching user list")
        users = self._manager.list_users()
        if len(users) == 0:
            LOG.i("No users found")
            return ExitStatus.SUCCESS

        for user in users:
            role = self._manager.get_user_role(user.identifier)
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

    def __init__(self, args: AppArgs, manager: UserManager):
        super().__init__(args)
        self._manager = manager

    def execute(self) -> int:
        user = User(identifier=self.args.user_identifier)
        LOG.d("Deleting user '%s'", user.identifier)
        self._manager.delete_user(user)
        LOG.i("Deleted user '%s'.", self.args.user_identifier)
        return ExitStatus.SUCCESS


class UserPermissionGetCommand(ServerCommand):
    """Implementation of `user permission get`."""

    def __init__(self, args: AppArgs, manager: UserManager):
        super().__init__(args)
        self._manager = manager

    def execute(self) -> int:
        user = User(identifier=self.args.user_identifier)
        permission_key = _create_permission_key(self.args.user_permission_key)
        LOG.d(
            "Getting permission '%s' for user '%s'",
            permission_key,
            user.identifier,
        )
        value = self._manager.get_user_permission(user, permission_key)
        formatter = TableFormatter().set_headers("User", "Permission", "Value")
        formatter.add_row(
            user.identifier,
            self.args.user_permission_key,
            self._format_permission_value(value),
        )
        LOG.i("User permission:")
        self._print_table(formatter)
        return ExitStatus.SUCCESS

    def _format_permission_value(self, value):
        normalized_value = value.lower()
        if normalized_value == "true":
            return "On"
        if normalized_value == "false":
            return "Off"

        raise InvalidUserRequestException(
            f"Invalid permission value: {value}"
        )

class UserPermissionSetCommand(ServerCommand):
    """Implementation of `user permission set`."""

    def __init__(self, args: AppArgs, manager: UserManager):
        super().__init__(args)
        self._manager = manager

    def execute(self) -> int:
        user = User(identifier=self.args.user_identifier)
        permission_key = _create_permission_key(self.args.user_permission_key)
        LOG.d(
            "Setting permission '%s' for user '%s'",
            permission_key,
            user.identifier,
        )
        self._manager.set_user_permission(
            user,
            permission_key,
            self.args.user_permission_value,
        )
        LOG.i(
            "Set permission '%s' for user %s to %s",
            permission_key,
            user.identifier,
            self.args.user_permission_value,
        )
        return ExitStatus.SUCCESS
