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

from abc import ABC, abstractmethod

from raven.fathom.server.datastore.orm.model import Model


class DataAccessObject(ABC):
    """The abstract base class for a Data Access Object (DAO)."""

    @abstractmethod
    def create(self, record: Model):
        """Creates a record.

        Args:
            record (Model): The record to be created.

        Raises:
            FailedCreateQueryException: If the record could not be created.
        """

    @abstractmethod
    def update(self, record: Model):
        """Updates a record.

        Args:
            record (Model): The record to be updated.

        Raises:
            FailedUpdateQueryException: If the record could not be updated.
        """

    @abstractmethod
    def delete(self, record: Model):
        """Deletes a record.

        Args:
            record (Model): The record to be deleted.

        Raises:
            FailedDeleteQueryException: If the record could not be deleted.
        """
