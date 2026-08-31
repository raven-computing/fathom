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
"""Lower-level API to interact with a database."""

from abc import ABC, abstractmethod
from typing import Any, Type, TYPE_CHECKING
from collections.abc import Generator

from raven.fathom.server.exceptions import FathomServerException

if TYPE_CHECKING:
    from raven.fathom.server.datastore.orm.model import Model
    from raven.fathom.server.datastore._schema_updates import (
        DatabaseSchemaUpdate
    )


class DatabaseException(FathomServerException):
    """Base exception class for database-related errors
    in the Fathom server component.
    """


class DatabaseInitializationException(DatabaseException):
    """The initialization of an application database or related
    infrastructure has failed.
    """


class DatabaseNotFoundException(DatabaseException):
    """A connection attempt was made to connect to a
    database but it was not found.
    """


class DatabaseConnectionException(DatabaseException):
    """A connection to a database could not be established or closed."""


class DatabaseCommandException(DatabaseException):
    """A command or query submitted to the database has returned an error."""


class DatabaseSchema(ABC):
    """An application database schema."""

    @abstractmethod
    def get_models(self) -> list[Type["Model"]]:
        """Returns a list of data models in the database schema.

        Returns:
            list: A list of data `Model` class objects.
        """

    @abstractmethod
    def get_update_procedures(self) -> Generator["DatabaseSchemaUpdate"]:
        """Returns a list of database schema update procedures.

        Yields:
            DatabaseSchemaUpdate: All `DatabaseSchemaUpdate` objects.
        """


class Database(ABC):
    """An application database."""

    @abstractmethod
    def type_name(self) -> str:
        """Gets the name of this type of database.

        Returns:
            str: The name by which the implementation
                of this database is known.
        """

    @abstractmethod
    def connect(self):
        """Connects to this database.

        Raises:
            DatabaseNotFoundException: If the database could not be found.
            DatabaseConnectionException: If a connection to the database
                could not be established.
        """

    @abstractmethod
    def disconnect(self):
        """Disconnects from this database."""

    @abstractmethod
    def is_connected(self) -> bool:
        """Indicates whether a connection to this database
        is currently established.

        Returns:
            bool: `True` if currently connected,
                `False` if currently disconnected.
        """

    @abstractmethod
    def get_schema(self) -> DatabaseSchema:
        """Gets the schema of this database.

        Returns:
            DatabaseSchema: The schema of this database.
        """

    @abstractmethod
    def run_command(self, command: str, *args, **kwargs) -> Any:
        """Runs a database command.

        Args:
            command (str): An arbitrary command to run against the database.
            *args: Positional arguments for the command.
            **kwargs: Keyword arguments for the command.

        Returns:
            Any: The result of the command execution.
        """

    @abstractmethod
    def get_orm_provider(self) -> Any:
        """Returns the real provider instance for database
        access operations.

        Returns:
            The object used to perform database operations.
        """

    @abstractmethod
    def __enter__(self):
        """Opens a database connection and begins a transaction."""

    @abstractmethod
    def __exit__(self, ex_type, ex_value, ex_trace):
        """Commits the current transaction
        and closes the database connection.
        """
