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
"""Database schema consistency verification.

Provides a function to check that a set of data models are consistent with
an existing database schema.
"""

from typing import Type, Optional

from playhouse.reflection import Introspector

from raven.fathom.server.datastore.database import Database
from raven.fathom.server.datastore.database import DatabaseSchemaVerification
from raven.fathom.server.datastore.orm import Model


class _Result(DatabaseSchemaVerification):

    def __init__(
        self,
        ok: bool,
        missing_tables: Optional[list[str]],
        missing_columns: Optional[list[str]],
        extra_columns: Optional[list[str]]
    ):
        super().__init__()
        self._ok = ok
        self._missing_tables = missing_tables
        self._missing_columns = missing_columns
        self._extra_columns = extra_columns

    def ok(self) -> bool:
        return self._ok

    def to_string(self) -> str:
        if self._ok:
            return "OK"

        details = []

        if self._missing_tables:
            details.append(
                "Missing tables: " + ", ".join(self._missing_tables)
            )

        if self._missing_columns:
            details.append(
                "Missing table columns: " + "; ".join(self._missing_columns)
            )

        if self._extra_columns:
            details.append(
                "Extra table columns: " + "; ".join(self._extra_columns)
            )

        if not details:
            return "Schema verification failed"

        return "; ".join(details)


def verify_schema(
    models: list[Type[Model]],
    database: Database
) -> DatabaseSchemaVerification:
    """Compares a list of ORM models against the actual database schema.

    Args:
        models (list):
        database: (Database): 

    Returns:
        bool: 
    """
    introspector = Introspector.from_database(database.get_orm_provider())
    db_schema = introspector.generate_models()
    inconsistencies_found = False
    missing_tables = []
    missing_columns = []
    extra_columns = []
    for model in models:
        # pylint: disable=protected-access
        table_name = model._meta.table_name

        # Check if the table exists
        if table_name not in db_schema:
            # Table is defined in models but MISSING in the database
            inconsistencies_found = True
            missing_tables.append(table_name)
            continue

        # Compare columns
        actual_db_model = db_schema[table_name]

        expected_columns = set(model._meta.columns.keys())
        actual_columns = set(actual_db_model._meta.columns.keys())

        # Extract column names
        missing_in_db = expected_columns - actual_columns
        extra_in_db = actual_columns - expected_columns

        if missing_in_db:
            # Field is defined in model but missing column in database
            inconsistencies_found = True
            missing_columns.extend(
                f"{table_name}.{col}" for col in sorted(missing_in_db)
            )

        if extra_in_db:
            # Extra column in database but field not defined in model
            inconsistencies_found = True
            extra_columns.extend(
                f"{table_name}.{col}" for col in sorted(extra_in_db)
            )

    return _Result(
        not inconsistencies_found,
        missing_tables,
        missing_columns,
        extra_columns,
    )
