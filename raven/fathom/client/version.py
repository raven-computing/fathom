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
"""Fathom client version identification."""

from typing import Optional

from raven.fathom.base import determine_current_version
from raven.fathom.base import VersionStruct


class Version(VersionStruct):
    """The version of the Fathom client application."""

    @staticmethod
    def current() -> Optional["Version"]:
        """Detects the currently running Fathom client application version.

        Returns:
            Version: The current Fathom client application version
                or `None` if the version cannot be determined.
        """
        version = determine_current_version("raven-fathom-client")
        if version is not None:
            return Version(
                version.major,
                version.minor,
                version.patch,
                version.extension
            )

        return None
