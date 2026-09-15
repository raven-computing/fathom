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
"""Fathom client CLI utilities."""

from raven.fathom.base.context import APPLICATION_NAME
from raven.fathom.client.version import Version


def show_version(short_version: bool) -> bool:
    """Prints the Fathom client version information on stdout.

    Args:
        short_version (bool): Whether to show a short form of
            the version string.

    Returns:
        bool: `True` if successful, `False` if an error occurred.
    """
    version = Version.current()
    if version is None:
        print("Error: Application version could not be determined.")
        return False

    if short_version:
        print(version)
    else:
        dev = (
            " (DEVELOPMENT VERSION)"
            if version.is_development_version()
            else ""
        )
        print(f"{APPLICATION_NAME} client v{version}{dev}")

    return True
