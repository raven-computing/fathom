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
"""Server CLI command handling."""

import functools

from collections.abc import Callable
from typing import TYPE_CHECKING, TypeVar, TypeAlias

from raven.fathom.base import Command
from raven.fathom.server.datastore import DatabaseManager
from raven.fathom.server.startup import confirm_system_privileges

if TYPE_CHECKING:
    from raven.fathom.server.cli.arguments import AppArgs


class ServerCommand(Command):
    """Base class for all server CLI commands.

    Attributes:
        args (AppArgs): The `AppArgs` object used by the
            underlying CLI application.
    """

    def __init__(self, args: "AppArgs"):
        self.args = args
        super().__init__(args.command)


S = TypeVar("S", bound=ServerCommand)

ExecuteMethod: TypeAlias = Callable[[S], int]


def require_database(method: ExecuteMethod[S]) -> ExecuteMethod[S]:
    """Decorator that runs a command with an active database connection."""

    @functools.wraps(method)
    def wrapped(instance: S) -> int:
        db = DatabaseManager().get_database()
        should_disconnect = not db.is_connected()
        if should_disconnect:
            db.connect()

        try:
            return method(instance)
        finally:
            if should_disconnect and db.is_connected():
                db.disconnect()

    return wrapped


def require_privileges(method: ExecuteMethod[S]) -> ExecuteMethod[S]:
    """Decorator that enforces successful system-user authentication."""

    @functools.wraps(method)
    def wrapped(instance: S) -> int:
        confirm_system_privileges()
        return method(instance)

    return wrapped
