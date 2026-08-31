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
"""Primary data access API.

Use `DataAccess` to obtain data access objects (DAOs) for different entities in
the application. Each DAO provides methods for interacting with the underlying
data source, allowing general CRUD operations as well as domain-specific
queries and manipulations.
"""

from .api import DataAccess
from .api import DatastoreException
from .api import FailedQueryException
from .api import FailedCreateQueryException
from .api import FailedReadQueryException
from .api import FailedUpdateQueryException
from .api import FailedDeleteQueryException
from .api import IncoherentDatastoreStateException
from .base import DataAccessObject
from .user import UserDAO
from .project import ProjectDAO
