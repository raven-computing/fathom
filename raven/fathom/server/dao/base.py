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
"""General Data Access Object (DAO) API."""

from typing import Optional, Generic
from abc import ABC, abstractmethod

from raven.fathom.server.datastore.orm.model import M
from raven.fathom.server.datastore.orm.field import RecordId


class DataAccessObject(ABC, Generic[M]):
    """The abstract base class for a Data Access Object (DAO)."""

    @abstractmethod
    def create(self, record: M):
        """Creates a record.

        Args:
            record (M): The record of model `M` to be created.

        Raises:
            FailedCreateQueryException: If the record could not be created.
        """

    @abstractmethod
    def read(self, record_id: RecordId) -> Optional[M]:
        """Reads the record that has the specified ID in the datastore.

        Args:
            record_id (RecordId): The ID of the record to read.

        Returns:
            M: A single persisted record of model `M`. May be `None` if no
                record with the specified ID can be found in the datastore.

        Raises:
            FailedReadQueryException: If the record could not be read.
        """

    @abstractmethod
    def read_all(self) -> list[M]:
        """Reads all records of model `M` in the datastore.

        Returns:
            list[M]: A list of all records of model `M`.

        Raises:
            FailedReadQueryException: If the records could not be read.
        """

    @abstractmethod
    def update(self, record: M):
        """Updates a record.

        Args:
            record (M): The record of model `M` to be updated.

        Raises:
            FailedUpdateQueryException: If the record could not be updated.
        """

    @abstractmethod
    def delete(self, record: M):
        """Deletes a record.

        Args:
            record (M): The record of model `M` to be deleted.

        Raises:
            FailedDeleteQueryException: If the record could not be deleted.
        """
