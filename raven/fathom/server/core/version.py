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
"""Fathom server version identification."""

from typing import Optional

from raven.fathom.base import determine_current_version
from raven.fathom.base import VersionStruct, read_version_file
from raven.fathom.base import ApplicationContext


class Version(VersionStruct):
    """The version of the Fathom server application."""

    @staticmethod
    def current() -> Optional["Version"]:
        """Detects the currently running Fathom server application version.

        Returns:
            Version: The current Fathom server application version
                or `None` if the version cannot be determined.
        """
        version = determine_current_version("raven-fathom-server")
        if version is not None:
            return Version(
                version.major,
                version.minor,
                version.patch,
                version.extension
            )

        return None

    @staticmethod
    def previous() -> Optional["Version"]:
        """Detects the previously running Fathom server application version.

        Returns:
            Version: The previous Fathom server application version.

        Raises:
            FileIOException: If a version file cannot be read.
        """
        version = read_version_file(
            ApplicationContext.instance().get_working_directory()
        )
        if version is not None:
            return Version(
                version.major,
                version.minor,
                version.patch,
                version.extension
            )

        return None
