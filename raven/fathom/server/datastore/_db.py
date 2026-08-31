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
"""Implementation of the database API using peewee."""

import peewee

from raven.fathom.base import TypeCheck
from raven.fathom.server.datastore.database import Database
from raven.fathom.server.datastore.database import DatabaseConnectionException
from raven.fathom.server.datastore.database import DatabaseCommandException
from raven.fathom.server.datastore._schema import DatabaseSchemaImpl


class DatabaseImpl(Database):
    """Implementation of `Database` connecting through peewee."""

    def __init__(self, db):
        TypeCheck.require_arg(db, peewee.Database)
        self._db: peewee.Database = db

    def connect(self):
        try:
            self._db.connect(reuse_if_open=True)
        except peewee.PeeweeException as ex:
            raise DatabaseConnectionException(
                "Failed to connect to database"
            ) from ex

    def disconnect(self):
        try:
            self._db.close()
        except peewee.PeeweeException as ex:
            raise DatabaseConnectionException(
                "Failed to close database connection"
            ) from ex

    def is_connected(self):
        return not self._db.is_closed() and self._db.is_connection_usable()

    def get_schema(self):
        return DatabaseSchemaImpl()

    def run_command(self, command, *args, **kwargs):
        try:
            return self._db.connection().executescript(command)
        except peewee.PeeweeException as ex:
            raise DatabaseCommandException(
                f"Error while executing database command: {command}"
            ) from ex

    def get_orm_provider(self):
        return self._db

    def __enter__(self):
        try:
            self._db.__enter__()
        except peewee.PeeweeException as ex:
            raise DatabaseConnectionException(
                "Failed to connect to database"
            ) from ex

    def __exit__(self, ex_type, ex_value, ex_trace):
        try:
            self._db.__exit__(ex_type, ex_value, ex_trace)
        except peewee.PeeweeException as ex:
            raise DatabaseConnectionException(
                "Failed to close database connection"
            ) from ex
