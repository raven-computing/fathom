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
"""Internal database access layer."""

import logging

from typing import TYPE_CHECKING, Optional, Type, Final

import peewee

from raven.fathom.base import File
from raven.fathom.base import LogFormatterCLI
from raven.fathom.base import LogHandlerCLI
from raven.fathom.server.logging import Logger, FathomLogHandlerFile
from raven.fathom.server.datastore.database import (
    DatabaseInitializationException,
)
from raven.fathom.server.datastore._proxy import get_orm_proxy
from raven.fathom.server.datastore._sqlite import DatabaseSQLite

if TYPE_CHECKING:
    from raven.fathom.server.datastore.database import Database
    from raven.fathom.server.datastore.orm import Model


LOG = Logger.get()

_LOG_FORMAT_PREFIX: Final = "SQL:"

_LOGGER_NAME_ORM_IMPL: Final = "peewee"


def _db_proxy_init(db_proxy: peewee.Proxy, orm_provider):
    try:
        db_proxy.initialize(orm_provider)
    except peewee.PeeweeException as ex:
        raise DatabaseInitializationException(
            "Failed to initialize ORM database proxy"
        ) from ex


class DatabaseAccess:
    """Internal database access utilities."""

    @staticmethod
    def is_debug_logging_enabled() -> bool:
        """Indicates whether debug logging for the database ORM facilities
        is currently enabled.

        Returns:
            bool: `True` if debug logging is enabled,
                `False` if it is disabled.
        """
        logger = logging.getLogger(_LOGGER_NAME_ORM_IMPL)
        return logger.level == logging.DEBUG

    @staticmethod
    def set_debug_loggging_enabled(value: bool):
        """Enable or disable debug logging of database ORM facilities.

        Args:
            value (bool): Whether to enable (`True`) or disable (`False`).
        """
        logger = logging.getLogger(_LOGGER_NAME_ORM_IMPL)
        cli_handler = LogHandlerCLI()
        cli_handler.setFormatter(
            LogFormatterCLI(include_timestamp=True, prefix=_LOG_FORMAT_PREFIX)
        )
        logger.addHandler(cli_handler)
        file_handler = FathomLogHandlerFile()
        file_handler.setFormatter(
            LogFormatterCLI(
                include_timestamp=True,
                use_colours=False,
                prefix=_LOG_FORMAT_PREFIX
            )
        )
        logger.addHandler(file_handler)
        logger.setLevel(logging.DEBUG if value else logging.CRITICAL)

    @staticmethod
    def initialize_orm(db: "Database"):
        """Initializes the ORM database proxy with the given database.

        Args:
            db (Database): The database instance.
        """
        db_proxy = get_orm_proxy()
        orm_provider = db.get_orm_provider()
        LOG.d(
            "Initializing database ORM proxy %s with provider %s",
            db_proxy, orm_provider
        )
        _db_proxy_init(db_proxy, orm_provider)

    @staticmethod
    def create_schema_tables(db: "Database", models: list[Type["Model"]]):
        """Creates the schema tables for the given models in the database.

        Args:
            db (Database): The database instance.
            models (list): The list of `Model` classes.
        """
        provider = db.get_orm_provider()
        try:
            provider.create_tables(models)
        except peewee.PeeweeException as ex:
            LOG.e("Failed to create database tables for ORM models")
            raise DatabaseInitializationException from ex

    @staticmethod
    def create_database_instance_sqlite(file: Optional[File]) -> "Database":
        """Creates a SQLite database instance.

        Args:
            file (File): The file for the SQLite database file.

        Returns:
            Database: The SQLite database instance.
        """
        if file is not None:
            file = File(file)

        return DatabaseSQLite(file)
