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
"""Fathom base version identification and handling of version files."""

import re

from importlib import metadata
from functools import cache
from typing import Optional, TYPE_CHECKING

from raven.fathom.base.context import get_project_source_root
from raven.fathom.base.context import ApplicationContext, ApplicationMode

if TYPE_CHECKING:
    from raven.fathom.base.file import File


VERSION_FILE_NAME = "VERSION"

VERSION_REGEX = re.compile(
    r"^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
    r"(?:-(?P<extension>[a-zA-Z0-9.]*))?$"
)


def read_version_string(version: str) -> Optional["VersionStruct"]:
    """Reads the version string and returns the version information in it.

    Args:
        version (str): The version string to read.

    Returns:
        VersionStruct: The version information, or None if the version string
            is not correctly formatted.
    """
    match = VERSION_REGEX.match(version)
    if match:
        return VersionStruct(
            int(match.group("major")),
            int(match.group("minor")),
            int(match.group("patch")),
            match.group("extension") or ""
        )

    return None


def read_version_file(directory: "File") -> Optional["VersionStruct"]:
    """Reads the version file and returns the version information in it.

    Args:
        directory (File): The directory where the version file is located in.

    Returns:
        VersionStruct: The version information, or None if the version file
            does not exist or the data in it is not correctly formatted.

    Raises:
        FileIOException: If an I/O error occurs while reading the version file.
    """
    version_file = directory / VERSION_FILE_NAME
    if version_file.is_regular_file():
        version_lines = version_file.read_all_text_lines()
        if len(version_lines) > 0:
            version_text = version_lines[0].strip()
            return read_version_string(version_text)

    return None


def write_version_file(directory: "File", version: "VersionStruct"):
    """Writes the version information to the version file.

    Args:
        directory (File): The directory where the version file should
            be created or overwritten.
        version (VersionStruct): The version information to write to the file.

    Raises:
        FileIOException: If an I/O error occurs while writing the version file.
    """
    version_file = directory / VERSION_FILE_NAME
    version_file.write_all(str(version))


@cache
def determine_current_version(package_name: str) -> Optional["VersionStruct"]:
    """Attempts to detect the currently running application version.

    Args:
        package_name (str): The name of the package to detect the version for.

    Returns:
        VersionStruct: The current version of the Fathom base package, or None
            if the version cannot be determined.
    """
    ctx = ApplicationContext.instance()
    if ctx.get_application_mode() == ApplicationMode.PRODUCTION:
        try:
            meta_version = metadata.version(package_name)
            return read_version_string(meta_version)
        except (metadata.PackageNotFoundError, ValueError):
            return None
    else:
        src_root = get_project_source_root()
        if src_root is not None:
            return read_version_file(src_root)

    return None


class VersionStruct:
    """Version identification.

    Version extensions are only considered by their presence, but not further
    evaluated when comparing version objects. For example, the
    version '1.2.3' and '1.2.3-alpha' are not considered equal, the
    second version is considered less than the first one since it has
    an '-alpha' extension and the first one does not have any extension.
    As a second example, the two version
    objects '1.2.3-alpha' and '1.2.3-beta' are considered equal, even though
    the two extensions are different.
    """

    def __init__(
        self,
        major: int,
        minor: int,
        patch: int,
        extension: str = ""
    ):
        self._major = major
        self._minor = minor
        self._patch = patch
        self._extension = extension
        if extension and not extension.isalnum() and extension != ".":
            raise ValueError(
                "Version extension must be alphanumeric or empty"
            )

    @property
    def major(self) -> int:
        """The major version number, as an `int`."""
        return self._major

    @property
    def minor(self) -> int:
        """The minor version number, as an `int`."""
        return self._minor

    @property
    def patch(self) -> int:
        """The patch version number, as an `int`."""
        return self._patch

    @property
    def extension(self) -> str:
        """The extension to the version number, as a `str`.

        Does not include the leading dash ('-') character.
        May be an empty string if no extension is present.
        """
        return self._extension.lstrip("-")

    def is_development_version(self) -> bool:
        """Indicates whether this version is a development version.

        A development version is a snapshot version that is a result of
        ongoing development work and it is not intended for production use.

        Returns:
            bool: `True` if this version is a development version,
                `False` otherwise.
        """
        return self.extension == "dev"

    def __eq__(self, rhs):
        return all(map(lambda d: d == 0, self._diff(rhs)))

    def __ne__(self, rhs):
        return not self.__eq__(rhs)

    def __lt__(self, rhs: "VersionStruct"):
        return self._compare_to(rhs) < 0

    def __le__(self, rhs: "VersionStruct"):
        return self._compare_to(rhs) <= 0

    def __gt__(self, rhs: "VersionStruct"):
        return self._compare_to(rhs) > 0

    def __ge__(self, rhs: "VersionStruct"):
        return self._compare_to(rhs) >= 0

    def __str__(self):
        ext = ""
        if self.extension:
            ext = f"-{self.extension}"

        return f"{self.major}.{self.minor}.{self.patch}{ext}"

    def _compare_to(self, other):
        for diff in self._diff(other):
            if diff != 0:
                return -1 if diff < 0 else 1

        return 0

    def _diff(self, other):
        return (
            self.major - other.major,
            self.minor - other.minor,
            self.patch - other.patch,
            (0 if self.extension else 1) - (0 if other.extension else 1)
        )


class Version(VersionStruct):
    """The version of the Fathom base package."""

    @staticmethod
    def current() -> Optional["Version"]:
        """Detects the currently running Fathom base library version.

        Returns:
            Version: The current Fathom base library version
                or `None` if the version cannot be determined.
        """
        version = determine_current_version("raven-fathom-base")
        if version is not None:
            return Version(
                version.major,
                version.minor,
                version.patch,
                version.extension
            )

        return None
