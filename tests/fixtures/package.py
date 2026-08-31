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
"""Test fixtures for resource packages."""

from raven.fathom.base import File, TemporaryFile
from raven.fathom.base import Package, PackageableResourceCollection
from raven.fathom.base import PackageableResource

from tests.common import FathomTestFixture


class PackageableFile(PackageableResource):
    """A dummy `PackageableResource` for `File` objects."""

    def __init__(self, file: File):
        super().__init__()
        self.file = file

    def get_name(self):
        return self.file.name

    def get_data(self):
        return self.file.read_all_bytes()


class PackageableBytes(PackageableResource):
    """A dummy `PackageableResource` for `bytes` objects."""

    def __init__(self, name: str, data: bytes):
        super().__init__()
        self.name = name
        self.data = data

    def get_name(self):
        return self.name

    def get_data(self):
        return self.data


class DummyResourceCollection(PackageableResourceCollection):
    """A dummy `PackageableResourceCollection`."""

    def __init__(self):
        super().__init__()
        self._files = []
        self._bytes = []

    def add_file(self, file: File):
        """Add a file to the collection."""
        self._files.append(PackageableFile(file))

    def add_bytes(self, name: str, data: bytes):
        """Add bytes to the collection."""
        self._bytes.append(PackageableBytes(name, data))

    def get_resources(self):
        return self._files + self._bytes


class PackageFixture(FathomTestFixture):
    """Test fixture to set up packages."""

    _PACKED_PACKAGE_DATA = bytes()

    @classmethod
    def load_fixture(cls):
        collection = DummyResourceCollection()
        with TemporaryFile.create_temporary_directory() as tmp_dir:
            file_1 = tmp_dir / File("file_1")
            file_1.write_all("Data of file_1")
            collection.add_file(file_1)
            file_2 = tmp_dir / File("/tmp/file_2")
            file_2.write_all("Data of file_2")
            collection.add_file(file_2)
            package = Package(collection)
            package.pack()
            PackageFixture._PACKED_PACKAGE_DATA = package.get_bytes()

    @property
    def unpacked_package_resource(self) -> DummyResourceCollection:
        """A dummy `PackageableResourceCollection` object.

        Corresponds to the data in the `unpacked_package` property.
        """
        resource = self.empty_package_resource
        resource.add_bytes("file_1", b"Data of file_1")
        resource.add_bytes("file_2", b"Data of file_2")
        return resource

    @property
    def empty_package_resource(self) -> DummyResourceCollection:
        """A dummy empty `PackageableResourceCollection` object."""
        return DummyResourceCollection()

    @property
    def packed_package(self) -> Package:
        """A `Package` object in a packed state."""
        transport_format = Package.TransportFormat.ARCHIVE_ZIP
        packed_package = Package(PackageFixture._PACKED_PACKAGE_DATA)
        packed_package.transport_format = transport_format
        return packed_package

    @property
    def unpacked_package(self) -> Package:
        """A `Package` object in an unpacked state."""
        transport_format = Package.TransportFormat.ARCHIVE_ZIP
        unpacked_package = Package(self.unpacked_package_resource)
        unpacked_package.transport_format = transport_format
        return unpacked_package
