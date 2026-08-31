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
"""Management of database instances during the application lifecycle."""

from typing import Optional

from raven.fathom.base import ApplicationContext
from raven.fathom.base import File, FileIOException
from raven.fathom.base.decorators import singleton
from raven.fathom.server.logging import Logger
from raven.fathom.server.datastore.database import Database
from raven.fathom.server.datastore._db_access import DatabaseAccess


LOG = Logger.get()


@singleton
class DatabaseManager:
    """Manages database instances and access to it by application code."""

    def __init__(self):
        self._db: Optional[Database] = None
        self._db_file: Optional[File] = None
        self._in_mem: bool = False

    def locate_application_database(self) -> bool:
        """Attemps to find out how to connect to the application database.

        Returns:
            bool: `True` if the database was located, `False` otherwise.
        """
        if self._db is not None:
            return True

        ctx = ApplicationContext.instance()
        datastore_directory = self._get_datastore_directory(ctx)
        if datastore_directory is None:
            return False

        database_name = ctx.get_project_identifier()
        self._db_file = datastore_directory / f"{database_name}.db"
        return True

    def check_database_exists(self) -> bool:
        """Checks if a located database exists.

        Returns:
            bool: `True` if the database exists and can potentially
                be connected to, `False` if the database could not be found.
        """
        if self._db_file is not None:
            return self._db_file.is_regular_file()

        return False

    def get_database(self) -> Database:
        """Gets a reference to an initialized application database.

        Returns:
            Database: The application database.
        """
        if self._db is not None:
            return self._db

        self._init_db()
        assert self._db is not None
        return self._db

    def shutdown(self):
        """Executes database shutdown procedures."""
        if self._db is not None and self._db.is_connected():
            self._db.disconnect()

        self._db = None
        self._db_file = None
        self._in_mem = False

    def initialize_empty_database(self):
        """Initializes the database schema with no data."""
        assert self._db is not None
        models = self._db.get_schema().get_models()
        DatabaseAccess.create_schema_tables(self._db, models)

    def set_in_memory_storage(self, value: bool):
        """Sets whether to activate in-memory data storage.

        Args:
            value (bool): Whether in-memory mode should be active.
        """
        self._in_mem = value

    def is_debug_logging_enabled(self) -> bool:
        """Indicates whether debug logging for the datastore facilities
        is currently enabled.

        Returns:
            bool: `True` if debug logging is enabled,
                `False` if it is disabled.
        """
        return DatabaseAccess.is_debug_logging_enabled()

    def set_debug_loggging_enabled(self, value: bool):
        """Enable or disable debug logging for the datastore facilities.

        Args:
            value (bool): Whether to enable (`True`) or disable (`False`).
        """
        DatabaseAccess.set_debug_loggging_enabled(value)

    def _get_datastore_directory(
        self,
        ctx: ApplicationContext
    ) -> Optional[File]:
        datastore_directory = ctx.get_working_directory() / "ds"
        if not datastore_directory.exists():
            return self._create_datastore(datastore_directory)

        return datastore_directory

    def _create_datastore(self, datastore_directory: File) -> Optional[File]:
        try:
            datastore_directory.create_directory()
            return datastore_directory
        except FileIOException as ex:
            LOG.e(
                "Failed to create datastore directory. "
                "A file I/O error has occurred: %s",
                str(ex)
            )
            return None

    def _init_db(self):
        LOG.d("Initializing database object")
        file = self._db_file
        if self._in_mem:
            LOG.d("A database with in-memory mode was requested")
            file = None

        db = DatabaseAccess.create_database_instance_sqlite(file)
        LOG.d("Obtained database object %s", db)
        self._set_active_db(db)

    def _set_active_db(self, database: Database):
        DatabaseAccess.initialize_orm(database)
        self._db = database
