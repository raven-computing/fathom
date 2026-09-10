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
"""Data access API.

Application code should use `DataAccess.instance()` to obtain data access
objects to interact with the application's data source.
"""

from abc import abstractmethod
from typing import Type, TypeVar

from raven.fathom.base import Interface
from raven.fathom.base.decorators import inject
from raven.fathom.server.dao.base import DataAccessObject
from raven.fathom.server.dao.user import UserDAO
from raven.fathom.server.dao.project import ProjectDAO
from raven.fathom.server.datastore.orm.model import Model
from raven.fathom.server.exceptions import FathomServerException


class DatastoreException(FathomServerException):
    """Base exception type for all errors related to data access
    through the public API.
    """


class FailedQueryException(DatastoreException):
    """A query made to the datastore has failed exceptionally."""


class FailedCreateQueryException(FailedQueryException):
    """A CREATE query made to the datastore has failed exceptionally."""


class FailedReadQueryException(FailedQueryException):
    """A READ query made to the datastore has failed exceptionally."""


class FailedUpdateQueryException(FailedQueryException):
    """An UPDATE query made to the datastore has failed exceptionally."""


class FailedDeleteQueryException(FailedQueryException):
    """A DELETE query made to the datastore has failed exceptionally."""


class IncoherentDatastoreStateException(DatastoreException):
    """Raised by a data access implementation when a query encounters an
    incoherent state in the underlying datastore, e.g. a missing record
    that must exist given the existence of another record.
    """


M = TypeVar("M", bound=Model)


@inject
class DataAccess(Interface):
    """Application API for data access."""

    @abstractmethod
    def data(self, model: Type[M]) -> DataAccessObject[M]:
        """Obtains a generic data access object.

        Args:
            model: The class of the data model to access,
                as a type of model `M`.

        Returns:
            DataAccessObject[M]: A DAO to handle generic data access
                of model `M`.
        """

    @abstractmethod
    def users(self) -> UserDAO:
        """Provides access to user data.

        Returns:
            UserDAO: A data access object.
        """

    @abstractmethod
    def projects(self) -> ProjectDAO:
        """Provides access to project data.

        Returns:
            ProjectDAO: A data access object.
        """
