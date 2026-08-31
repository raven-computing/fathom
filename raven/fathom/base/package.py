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
"""Contains class definitions for transmittable packages.

A package is an object that represents a collection of resources and that
can be serialized for the purpose of transferring those resources to a
potentially remote entity over a network connection.

A single resource is represented by a `PackageableResource` object.
An arbitrary entity can be made packageable by
implementing `PackageableResourceCollection`. An instance of such an entity
can then be used in the initializer of the `Package` class.

Classes of this module may raise a `PackageOperationException` to indicate
failure or errors.
"""

import re

from enum import Enum
from abc import ABC, abstractmethod
from typing import Union, Optional, Iterable
from dataclasses import dataclass, field
from io import StringIO

from raven.fathom.base.file import File, TemporaryFile, FileIOException
from raven.fathom.base.archive import ArchiveFile, ArchiveFileMember
from raven.fathom.base.archive import ArchiveFileIOException
from raven.fathom.base.typing import TypeCheck
from raven.fathom.base.exceptions import FathomBaseException


class PackageOperationException(FathomBaseException):
    """A failed package operation."""


class PackageableResource(ABC):
    """A resource that can be packaged."""

    @abstractmethod
    def get_name(self) -> str:
        """Gets the name of the packageable resource.

        Returns:
            str: The name of the resource.
        """

    @abstractmethod
    def get_data(self) -> Union[bytes, File]:
        """Gets the data of the packageable resource.

        Returns:
            bytes: The raw data of the resource, as a `bytes` object.
                May be a `File` object pointing to a file in the filesystem
                which should be used as the data source.
        """


class PackageableResourceCollection(ABC):
    """An iterable collection of packageable resources.

    Implementing classes must be able to provide an iterable
    collection of `PackageableResource` objects."""

    @abstractmethod
    def get_resources(self) -> Iterable[PackageableResource]:
        """Gets all resources.

        Returns:
            Iterable[PackageableResource]: An iterable
                of `PackageableResource` objects.
        """


@dataclass
class PackageMeta:
    """Metadata of a `Package` instance.

    Attributes:
        version (int): The packaging version in use. Applies per instance
            of a package.
        datadir (str): The name of the package's data directory, i.e. where
            all the files belonging to the payload are stored when unpacking.
        purpose (str): Description of what the package is used for.
        user (str): The name of the user who created the package.
    """

    version: int = field(default=1)

    datadir: str = field(default="data")

    purpose: Optional[str] = field(default=None)

    user: Optional[str] = field(default=None)


class Package:
    """A transmittable package of serializable resources.

    Attributes:
        state (Package.State): The state of the package.
        transport_format (Package.TransportFormat): The format of the data
            when packed.
        working_directory (Path): The directory where to execute
            packaging operations.
        data_directory (Path): The directory where the unpacked data resides.
        metadata (PackageMeta): The metadata of the package.
    """

    class State(Enum):
        """The state of the package."""

        UNPACKED = "unpacked"

        PACKED = "packed"

        def __str__(self):
            return self.value

    class TransportFormat(Enum):
        """Enumeration of supported transport formats a `Package` can have."""

        ARCHIVE_ZIP = "file-archive/zip"

        def __str__(self):
            return self.value

    # The name of the file inside of a package that
    # contains the encoded metadata.
    METADATA_FILE_NAME = "fathom_meta"

    def __init__(
        self,
        resource: Union[PackageableResourceCollection, bytes]
    ):
        """Initializes a new `Package` instance.

        Depending on the type of the `resource` argument, the package is either
        initialized in a packed or unpacked state. If the resource is a
        `PackageableResourceCollection`, the package is initialized in an
        unpacked state. If the resource is a `bytes` object, the package is
        initialized in a packed state.

        Args:
            resource (PackageableResourceCollection | bytes): The packageable
                resource to package.
        """
        self._state = Package.State.UNPACKED
        if isinstance(resource, bytes):
            self._state = Package.State.PACKED
        elif isinstance(resource, PackageableResourceCollection):
            self._state = Package.State.UNPACKED
        else:
            raise TypeError(
                "The argument to the Package initializer must be "
                "either bytes or PackageableResourceCollection"
            )

        self._transport_format = Package.TransportFormat.ARCHIVE_ZIP
        self._collection = resource
        self._working_directory = None
        self._data_directory = None
        self._unpacked_directory = None
        self._temp_dir = None
        self._is_released = False
        self._metadata = PackageMeta()

    @property
    def state(self) -> State:
        """The state of this package."""
        return self._state

    @property
    def transport_format(self) -> TransportFormat:
        """The transport format of this package."""
        return self._transport_format

    @transport_format.setter
    def transport_format(self, value):
        TypeCheck.require(value, Package.TransportFormat)
        self._transport_format = value

    @property
    def working_directory(self) -> Optional[File]:
        """The file of the working directory in the filesystem.

        May be `None` if no specific working directory is set, in which case
        executing packing operations will automatically manage a temporary
        working directory if needed.
        """
        return self._working_directory

    @working_directory.setter
    def working_directory(self, value):
        if value is not None:
            TypeCheck.require(value, File)

        self._working_directory = value

    @property
    def data_directory(self) -> Optional[File]:
        """The file of the root of the data directory.

        This attribute is only set after a package is unpacked,
        it is `None` otherwise. Users should check before usage
        whether the directory actually exists in the filesystem.
        """
        return self._data_directory

    @property
    def metadata(self) -> PackageMeta:
        """The metadata of this package, never `None`."""
        return self._metadata

    def pack(self):
        """Packages the resource.

        The packaged data will reside in memory.
        If a particular `PackageableResource` originated from a file, that file
        will not be modified or removed.
        The package will be in a packed state after this method completes.

        Raises:
            PackageOperationException: If this package cannot be packed.
        """
        if self.state == Package.State.PACKED:
            raise PackageOperationException(
                "Cannot pack package in PACKED state"
            )

        self._is_released = False
        archive = ArchiveFile(
            file=self._get_fs_pack_file(),
            file_format=self._map_transport_to_file_format()
        )
        self._add_resources_to_archive(archive)
        self._add_metadata_to_archive(archive)
        self._pack_resource_archive(archive)

        self._collection = self._read_packed_file(archive.file)
        self._clear_packed_file(archive.file)
        self._state = Package.State.PACKED

    def unpack(self):
        """Unpacks the resource.

        The unpacked data will reside in the filesystem.
        The package will be in an unpacked state after this method completes.

        Raises:
            PackageOperationException: If this package cannot be unpacked.
        """
        if self.state == Package.State.UNPACKED:
            raise PackageOperationException(
                "Cannot unpack package in UNPACKED state"
            )

        self._is_released = False
        pack_file = self._get_fs_pack_file()
        self._write_packed_data(pack_file)

        archive = ArchiveFile(
            file=pack_file,
            file_format=self._map_transport_to_file_format()
        )
        archive.auto_remove = True
        self._unpack_resource_archive(archive)

        self._metadata = self._read_package_meta_content(archive.file)
        self._unpacked_directory = archive.file
        self._data_directory = archive.file / File(self._metadata.datadir)
        self._state = Package.State.UNPACKED

    def get_bytes(self) -> bytes:
        """Gets the packed bytes of this package.

        Can only be used when the data of this package was previously packed
        or is already in that state since initialization.
        The returned bytes represent the package data as a whole, such that
        using those bytes to initialize another `Package` instance results in
        a new package being in a packed state and holding the same data as
        currently in this package.

        Returns:
            bytes: The packed bytes of this package.

        Raises:
            PackageOperationException: If the data of this package is
                not in a packed state.
        """
        if not isinstance(self._collection, bytes):
            raise PackageOperationException("Cannot get bytes")

        return self._collection

    def release(self):
        """Releases all held resources acquired during packaging operations.

        Raises:
            PackageOperationException: If an error occurs during
                the release operation.
        """
        self._clear_unpacked_dir()
        self._clear_temp_dir()
        self._data_directory = None
        self._working_directory = None
        self._is_released = True

    def is_released(self) -> bool:
        """Indicates whether this package has released its acquired resources.

        Call the `release()` method to release acquired resources explicitly.

        Returns:
            bool: `True` if resources have been released, `False` otherwise.
        """
        return self._is_released

    def _clear_unpacked_dir(self):
        if self._unpacked_directory is not None:
            if self._unpacked_directory.is_directory():
                self._unpacked_directory.remove()

            self._unpacked_directory = None

    def _add_resources_to_archive(self, archive):
        datadir = self.metadata.datadir + "/"
        assert isinstance(self._collection, PackageableResourceCollection)
        for resource in self._collection.get_resources():
            member_name = datadir + resource.get_name()
            try:
                archive.add(
                    ArchiveFileMember(member_name, resource.get_data())
                )
            except ArchiveFileIOException as ex:
                raise PackageOperationException(
                    f"Failed to add resource '{member_name}' to archive"
                ) from ex

    def _add_metadata_to_archive(self, archive):
        try:
            archive.add(
                ArchiveFileMember(
                    Package.METADATA_FILE_NAME,
                    content=self._create_package_meta_content()
                )
            )
        except ArchiveFileIOException as ex:
            raise PackageOperationException(
                "Failed to add metadata file to archive"
            ) from ex

    def _pack_resource_archive(self, archive):
        try:
            archive.pack()
        except ArchiveFileIOException as ex:
            raise PackageOperationException("Failed to pack resources") from ex

    def _unpack_resource_archive(self, archive):
        try:
            archive.extract()
        except ArchiveFileIOException as ex:
            raise PackageOperationException(
                "Failed to unpack resources"
            ) from ex

    def _map_transport_to_file_format(self):
        mapping = {
            Package.TransportFormat.ARCHIVE_ZIP: ArchiveFile.Format.ZIP,
        }
        mapped = mapping.get(self.transport_format)
        if mapped is None:
            raise PackageOperationException(
                "No mapping from transport to file format found"
            )

        return mapped

    def _get_fs_pack_file(self):
        try:
            if self._working_directory is not None:
                base_dir = self._working_directory
                if not base_dir.is_directory():
                    raise PackageOperationException(
                        "Cannot perform package operation in non-existing "
                        f"working directory: '{base_dir}'"
                    )

            else:
                self._temp_dir = TemporaryFile.create_temporary_directory(
                    prefix="fathom-"
                )
                base_dir = self._temp_dir

            return TemporaryFile.create_temporary_file(
                in_directory=base_dir,
                prefix="pkge_",
                suffix=self._map_transport_to_file_format().file_extension()
            )
        except FileIOException as ex:
            raise PackageOperationException(
                "Failed to create temporary file during pack operation"
            ) from ex

    def _clear_temp_dir(self):
        if self._temp_dir is not None:
            try:
                if self._temp_dir.is_directory():
                    self._temp_dir.remove()
            except FileIOException as ex:
                raise PackageOperationException(
                    "Failed to clear temporary package directory "
                    f"at '{self._temp_dir}'"
                ) from ex

            self._temp_dir = None

    def _read_packed_file(self, file):
        try:
            return file.read_all_bytes()
        except FileIOException as ex:
            raise PackageOperationException(
                "Failed to read packed file"
            ) from ex

    def _clear_packed_file(self, file):
        try:
            file.remove()
        except FileIOException as ex:
            raise PackageOperationException(
                "Failed to remove packed file"
            ) from ex

    def _write_packed_data(self, file):
        try:
            file.write_all(self._collection)
        except FileIOException as ex:
            raise PackageOperationException(
                "Failed to write packed data to file"
            ) from ex

        self._collection = None

    def _create_package_meta_content(self):
        meta = StringIO()
        meta.write(f"[Fathom-Package-Meta-v{self._metadata.version}]\n")
        meta.write(f"Datadir={self._metadata.datadir}\n")
        if self._metadata.purpose is not None:
            meta.write(f"Purpose={self._metadata.purpose}\n")

        if self._metadata.user is not None:
            meta.write(f"User={self._metadata.user}\n")

        return meta.getvalue().encode("UTF-8")

    def _read_package_meta_content(self, file):
        file = file / File(Package.METADATA_FILE_NAME)
        metadata = PackageMeta()
        lines = None
        try:
            lines = file.read_all_text_lines(include_empty=False)
        except FileIOException as ex:
            raise PackageOperationException(
                f"Failed to read package metadata file at '{file}'"
            ) from ex

        if lines is None or len(lines) == 0:
            return metadata

        line_0 = re.match(r"\[Fathom\-Package\-Meta-v(\d+)\]", lines[0])
        if line_0 is None:
            raise PackageOperationException(
                "Invalid package metadata format: Invalid metadata header"
            )

        version = line_0.group(1)
        metadata.version = int(version)
        for line in lines[1:]:
            line_vals = line.split("=", maxsplit=1)
            self._assign_package_meta_attr(metadata, line_vals)

        return metadata

    def _assign_package_meta_attr(self, metadata, line_vals):
        if len(line_vals) != 2:
            raise PackageOperationException(
                "Invalid package metadata format: Line must be key-value pair"
            )

        line_key = line_vals[0]
        line_value = line_vals[1].strip()
        if line_key == "Datadir":
            metadata.datadir = line_value
        elif line_key == "Purpose":
            metadata.purpose = line_value
        elif line_key == "User":
            metadata.user = line_value
