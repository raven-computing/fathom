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
"""ORM queries.

Provides Query classes for datastore CRUD operations.
"""

from typing import Optional, Union, Generic, TypeVar

import peewee as orm_impl

from raven.fathom.server.datastore.orm import Model
from raven.fathom.server.dao import (
    FailedCreateQueryException,
    FailedReadQueryException,
    FailedUpdateQueryException,
    FailedDeleteQueryException,
)


M = TypeVar("M", bound=Model)


class CreateQuery(Generic[M]):
    """An ORM query to create records of model `M`."""

    def __init__(self, record: M):
        self._record = record

    def execute(self):
        """Executes the create query."""
        try:
            self._record.save()
        except orm_impl.PeeweeException as ex:
            raise FailedCreateQueryException("Failed create query") from ex


class ReadQuery(Generic[M]):
    """An ORM query to read records of model `M`."""

    def __init__(self, query: orm_impl.Query):
        self.query = query

    def find_one(self) -> Optional[M]:
        """Executes the read query and returns
        the result as a single record or `None`.
        """
        try:
            result = self.query.execute()
            if len(result) == 0:
                return None

            return result[0]
        except orm_impl.DoesNotExist:
            return None

    def execute(self) -> list[M]:
        """Executes the read query and returns
        the result as a list of records.
        """
        try:
            return list(self.query)
        except orm_impl.PeeweeException as ex:
            raise FailedReadQueryException("Failed read query") from ex


class UpdateQuery(Generic[M]):
    """An ORM query to update records of model `M`."""

    def __init__(self, record: M):
        self._record = record

    def execute(self):
        """Executes the udpate query."""
        try:
            self._record.save()
        except orm_impl.PeeweeException as ex:
            raise FailedUpdateQueryException("Failed update query") from ex


class DeleteQuery(Generic[M]):
    """An ORM query to delete records of model `M`."""

    def __init__(self, query: Union[orm_impl.Query, M]):
        self._query = query
        self._record = None
        if isinstance(query, Model):
            self._record = query
            self._query = None

    def execute(self):
        """Executes the delete query."""
        try:
            if self._query is not None:
                assert isinstance(self._query, orm_impl.Query)
                self._query.execute()
            elif self._record is not None:
                self._record.delete_instance()
        except orm_impl.PeeweeException as ex:
            raise FailedDeleteQueryException("Failed delete query") from ex
