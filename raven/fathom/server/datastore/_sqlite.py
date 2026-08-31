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
"""Access to SQLite databases.

Using the peewee ORM to interact with SQLite databases.
"""

from typing import Optional

import peewee

from raven.fathom.base import File
from raven.fathom.base import TypeCheck
from raven.fathom.server.logging import Logger
from raven.fathom.server.datastore.database import DatabaseConnectionException
from raven.fathom.server.datastore._db import DatabaseImpl


LOG = Logger.get()


class DatabaseSQLite(DatabaseImpl):
    """Implementation of `Database` connecting to an SQLite database."""

    def __init__(self, file: Optional[File]):
        if file is not None:
            TypeCheck.require_arg(file, File)

        self._file = file
        super().__init__(
            peewee.SqliteDatabase(
                database=None,
                pragmas={"foreign_keys": 1},
                autoconnect=False,
            )
        )

    @property
    def file(self) -> Optional[File]:
        """The `File` of this SQLite database instance. May be `None`."""
        return self._file

    def type_name(self):
        return "SQLite"

    def connect(self):
        db_connection = ":memory:" if self._file is None else self._file.path
        LOG.d("Connecting to SQLite database: '%s'", db_connection)
        self._init(db_connection)
        super().connect()

    def disconnect(self):
        LOG.d("Disconnecting from SQLite database")
        super().disconnect()

    def _init(self, connection):
        try:
            self._db.init(connection)
        except peewee.PeeweeException as ex:
            LOG.e("Error while initializing database connection")
            raise DatabaseConnectionException(
                f"Failed to initialize database connection to {connection}"
            ) from ex
