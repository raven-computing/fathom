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
"""Database schema updates.

Provides an implementation of the `UpdateProcedure` ABC for updating database
schemas from one application version to another.
"""

from typing import Optional

import peewee

from raven.fathom.server.version import Version
from raven.fathom.server.logging import Logger
from raven.fathom.server.datastore.database import Database
from raven.fathom.server.updates import UpdateProcedure
from raven.fathom.server.updates import FailedUpdateProcedureException
from raven.fathom.server.updates._db_schema import Procedure
from raven.fathom.server.updates._db_schema import load_schema_update_list


LOG = Logger.get()


class DatabaseSchemaUpdate(UpdateProcedure):
    """An application update procedure responsible for updating the
    schema of an existing database.
    """

    def __init__(self, target_version: Version, procedure: Procedure):
        super().__init__(target_version)
        if not callable(procedure):
            raise TypeError(
                "Invalid argument 'procedure': Expected a callable but "
                f"found object of type {type(procedure)}"
            )

        self._callable_procedure = procedure
        self._database: Optional[Database] = None

    def apply(self):
        if self._database is None:
            raise FailedUpdateProcedureException(
                "No database set for schema update"
            )

        LOG.d("Calling schema update procedure %s", self._callable_procedure)
        try:
            self._callable_procedure(self._database.get_orm_provider())
        except (ValueError, peewee.DatabaseError) as error:
            raise FailedUpdateProcedureException(
                "Failed to apply database schema update procedure for "
                f"update to version {self.target_version}\n\n    "
                f"[{type(error).__name__}]: {error}\n"
            ) from None
        except Exception as ex:
            raise FailedUpdateProcedureException(
                "An unexpected error has occurred while applying a database "
                f"schema update procedure for version {self.target_version}"
            ) from ex

    def use_database(self, database: Database):
        """Sets this database schema update to use the specified
        database when it is applied.

        Args:
            database (Database): The `Database` for which this schema
                update should be applied.
        """
        self._database = database

    @staticmethod
    def get_all_procedures():
        """Gets all database schema update procedures.

        Yields:
            DatabaseSchemaUpdate: All known `DatabaseSchemaUpdate` objects.
        """
        return (
            DatabaseSchemaUpdate(version, procedure)
            for version, procedure in load_schema_update_list()
        )
