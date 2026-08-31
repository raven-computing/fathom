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
"""Application update procedures.

Use the `UpdateManager` class to check the update state and apply changes to
the state of the application in persistent storage after the application code
was updated in the filesystem.

All actions that might need to run after an application update must implement
the `UpdateProcedure` ABC.
"""

from .manager import UpdateManager
from .manager import FailedApplicationUpdateException
from .manager import FailedDatabaseSchemaUpdateException
from .procedure import UpdateProcedure
from .procedure import FailedUpdateProcedureException
