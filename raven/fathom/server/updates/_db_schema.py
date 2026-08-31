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
"""Application update procedures for database schemas.

Each schema update procedure must be implemented as a function that takes
a peewee `Database` object as its only argument and performs the necessary
schema changes on that database.
"""

# pylint: disable=W0401,W0611,W0614

from typing import TypeAlias, Callable, Any

from playhouse.migrate import migrate
from playhouse.migrate import Database
from playhouse.migrate import SqliteMigrator

from raven.fathom.server.logging import Logger
from raven.fathom.server.version import Version
from raven.fathom.server.models import *


LOG = Logger.get()

Procedure: TypeAlias = Callable[[Any], None]


# An example schema update:

# def _update_database_schema_to_version_1_2_3(db: Database):
#     LOG.i("Updating database schema to version 1.2.3")
#     sqlite = SqliteMigrator(db)
#     migrate(
#         sqlite.add_column("user", "something", User.something),
#         sqlite.drop_column("user", "something"),
#     )
#     LOG.i("Update of database schema to version 1.2.3 was successful")


def load_schema_update_list() -> list[tuple[Version, Procedure]]:
    """Loads all available database schema update procedure functions.

    Returns:
        list: A `list` of 2-tuple items, each with a target `Version`
            and a `Procedure` callable to be applied in order to
            reach that target version.
    """
    return [
        # (Version(1, 2, 3), _update_database_schema_to_version_1_2_3),
    ]
