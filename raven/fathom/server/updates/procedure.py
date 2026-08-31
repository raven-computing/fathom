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
"""Application update procedure.

Declares an ABC that must be implemented by all application update procedures.
"""

from abc import ABC, abstractmethod

from raven.fathom.server.version import Version
from raven.fathom.server.exceptions import FathomServerException


class FailedUpdateProcedureException(FathomServerException):
    """Raised when an application update procedure has failed."""


class UpdateProcedure(ABC):
    """A procedure that must be applied after an application update.

    Attributes:
        target_version (Version): The applicable version to update to.
    """

    def __init__(self, target_version: Version):
        """Initializes a new `UpdateProcedure` instance applicable
        for the given target version.

        Args:
            target_version (Version): The target version for which this
                update procedure should be applied.
        """
        self.target_version: Version = target_version

    @abstractmethod
    def apply(self):
        """Applies this update procedure.

        Raises:
            FailedUpdateProcedureException: If the procedure fails.
        """
