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
"""Unit tests for the base package module."""

from raven.fathom.base import Package, PackageOperationException
from raven.fathom.base import File
from raven.fathom.base.package import PackageMeta

from tests.unit import TestCase
from tests.fixtures import PackageFixture


class TestPackageMeta(TestCase):
    """Unit tests for the `PackageMeta` class."""

    def test_default_values(self):
        meta = PackageMeta()
        self.assertEqual(meta.version, 1)
        self.assertEqual(meta.datadir, "data")
        self.assertIsNone(meta.purpose)
        self.assertIsNone(meta.user)

    def test_custom_values(self):
        meta = PackageMeta(
            version=2,
            datadir="custom_dir",
            purpose="test purpose",
            user="testuser"
        )
        self.assertEqual(meta.version, 2)
        self.assertEqual(meta.datadir, "custom_dir")
        self.assertEqual(meta.purpose, "test purpose")
        self.assertEqual(meta.user, "testuser")


class TestPackageState(TestCase):
    """Unit tests for the `Package.State` enum."""

    def test_unpacked_state_value(self):
        self.assertEqual(
            Package.State.UNPACKED.value,
            "unpacked"
        )

    def test_packed_state_value(self):
        self.assertEqual(
            Package.State.PACKED.value,
            "packed"
        )

    def test_state_string_representation(self):
        self.assertEqual(str(Package.State.UNPACKED), "unpacked")
        self.assertEqual(str(Package.State.PACKED), "packed")


class TestPackageTransportFormat(TestCase):
    """Unit tests for the `Package.TransportFormat` enum."""

    def test_archive_zip_value(self):
        self.assertEqual(
            Package.TransportFormat.ARCHIVE_ZIP.value,
            "file-archive/zip"
        )

    def test_format_string_representation(self):
        self.assertEqual(
            str(Package.TransportFormat.ARCHIVE_ZIP),
            "file-archive/zip"
        )


class TestPackage(TestCase, PackageFixture):
    """Unit tests for the `Package` class."""

    def setUp(self):
        super().setUp()
        File.get_file_system().flush_system()

    def test_init_with_resource_collection(self):
        resource = self.unpacked_package_resource
        package = Package(resource)
        self.assertEqual(package.state, Package.State.UNPACKED)
        self.assertEqual(
            package.transport_format,
            Package.TransportFormat.ARCHIVE_ZIP
        )
        self.assertIsNone(package.working_directory)
        self.assertIsNone(package.data_directory)
        self.assertIsNotNone(package.metadata)
        self.assertFalse(package.is_released())

    def test_init_with_bytes(self):
        data = b"some packed data"
        package = Package(data)
        self.assertEqual(package.state, Package.State.PACKED)
        self.assertEqual(
            package.transport_format,
            Package.TransportFormat.ARCHIVE_ZIP
        )
        self.assertIsNone(package.working_directory)
        self.assertIsNone(package.data_directory)
        self.assertIsNotNone(package.metadata)
        self.assertFalse(package.is_released())

    def test_init_with_invalid_type(self):
        with self.assertRaises(TypeError) as raised:
            Package("invalid string type") # type: ignore

        self.assertIn(
            "must be either bytes or PackageableResourceCollection",
            str(raised.exception)
        )

    def test_init_with_none(self):
        with self.assertRaises(TypeError):
            Package(None) # type: ignore

    def test_init_with_dict(self):
        with self.assertRaises(TypeError):
            Package({"key": "value"}) # type: ignore

    def test_state_property(self):
        unpacked = self.unpacked_package
        self.assertEqual(unpacked.state, Package.State.UNPACKED)

        packed = self.packed_package
        self.assertEqual(packed.state, Package.State.PACKED)

    def test_transport_format_get(self):
        package = self.unpacked_package
        self.assertEqual(
            package.transport_format,
            Package.TransportFormat.ARCHIVE_ZIP
        )

    def test_transport_format_set(self):
        package = self.unpacked_package
        package.transport_format = Package.TransportFormat.ARCHIVE_ZIP
        self.assertEqual(
            package.transport_format,
            Package.TransportFormat.ARCHIVE_ZIP
        )

    def test_transport_format_set_invalid_type(self):
        package = self.unpacked_package
        with self.assertRaises(TypeError):
            package.transport_format = "invalid"

    def test_working_directory_get_default(self):
        package = self.unpacked_package
        self.assertIsNone(package.working_directory)

    def test_working_directory_set(self):
        package = self.unpacked_package
        work_dir = File("/tmp/working")
        package.working_directory = work_dir
        self.assertEqual(package.working_directory, work_dir)

    def test_working_directory_set_none(self):
        package = self.unpacked_package
        package.working_directory = File("/tmp/test")
        package.working_directory = None
        self.assertIsNone(package.working_directory)

    def test_working_directory_set_invalid_type(self):
        package = self.unpacked_package
        with self.assertRaises(TypeError):
            package.working_directory = "/tmp/invalid"

    def test_data_directory_default(self):
        package = self.unpacked_package
        self.assertIsNone(package.data_directory)

    def test_metadata_property(self):
        package = self.unpacked_package
        metadata = package.metadata
        self.assertIsNotNone(metadata)
        self.assertIsInstance(metadata, PackageMeta)

    def test_pack_unpacked_package(self):
        package = self.unpacked_package
        self.assertEqual(package.state, Package.State.UNPACKED)

        package.pack()

        self.assertEqual(package.state, Package.State.PACKED)
        self.assertFalse(package.is_released())

    def test_pack_already_packed_raises_error(self):
        package = self.packed_package
        self.assertEqual(package.state, Package.State.PACKED)

        with self.assertRaises(PackageOperationException) as raised:
            package.pack()

        self.assertIn("PACKED state", str(raised.exception))

    def test_pack_with_working_directory(self):
        package = self.unpacked_package
        work_dir = File("/tmp/test_work_dir")
        work_dir.create_directory_tree()
        package.working_directory = work_dir

        package.pack()

        self.assertEqual(package.state, Package.State.PACKED)

    def test_pack_with_nonexistent_working_directory(self):
        package = self.unpacked_package
        work_dir = File("/tmp/nonexistent_dir")
        package.working_directory = work_dir

        with self.assertRaises(PackageOperationException) as raised:
            package.pack()

        self.assertIn("non-existing working directory", str(raised.exception))

    def test_pack_with_metadata(self):
        package = self.unpacked_package
        package.metadata.purpose = "test purpose"
        package.metadata.user = "testuser"

        package.pack()

        self.assertEqual(package.state, Package.State.PACKED)

    def test_pack_empty_resource_collection(self):
        resource = self.empty_package_resource
        package = Package(resource)

        package.pack()

        self.assertEqual(package.state, Package.State.PACKED)

    def test_unpack_packed_package(self):
        package = self.packed_package
        self.assertEqual(package.state, Package.State.PACKED)

        package.unpack()

        self.assertEqual(package.state, Package.State.UNPACKED)
        self.assertIsNotNone(package.data_directory)
        self.assertFalse(package.is_released())

    def test_unpack_already_unpacked_raises_error(self):
        package = self.unpacked_package
        self.assertEqual(package.state, Package.State.UNPACKED)

        with self.assertRaises(PackageOperationException) as raised:
            package.unpack()

        self.assertIn("UNPACKED state", str(raised.exception))

    def test_unpack_with_working_directory(self):
        package = self.packed_package
        work_dir = File("/tmp/test_unpack_dir")
        work_dir.create_directory_tree()
        package.working_directory = work_dir

        package.unpack()

        self.assertEqual(package.state, Package.State.UNPACKED)
        self.assertIsNotNone(package.data_directory)

    def test_unpack_data_directory_accessible(self):
        package = self.packed_package
        package.unpack()

        data_dir = package.data_directory
        self.assertIsNotNone(data_dir)
        self.assertIsInstance(data_dir, File)

    def test_unpack_metadata_extracted(self):
        resource = self.unpacked_package_resource
        package = Package(resource)
        package.metadata.purpose = "custom purpose"
        package.metadata.user = "custom_user"
        package.pack()

        packed_data = package.get_bytes()
        new_package = Package(packed_data)
        new_package.unpack()

        self.assertEqual(new_package.metadata.purpose, "custom purpose")
        self.assertEqual(new_package.metadata.user, "custom_user")

    def test_get_bytes_from_packed_package(self):
        package = self.packed_package
        data = package.get_bytes()

        self.assertIsInstance(data, bytes)
        self.assertGreater(len(data), 0)

    def test_get_bytes_from_unpacked_package_raises_error(self):
        package = self.unpacked_package

        with self.assertRaises(PackageOperationException) as raised:
            package.get_bytes()

        self.assertIn("Cannot get bytes", str(raised.exception))

    def test_get_bytes_after_pack(self):
        package = self.unpacked_package
        package.pack()

        data = package.get_bytes()

        self.assertIsInstance(data, bytes)
        self.assertGreater(len(data), 0)

    def test_get_bytes_multiple_times(self):
        package = self.packed_package

        data1 = package.get_bytes()
        data2 = package.get_bytes()

        self.assertEqual(data1, data2)

    def test_release_unpacked_package(self):
        package = self.unpacked_package
        self.assertFalse(package.is_released())

        package.release()

        self.assertTrue(package.is_released())
        self.assertIsNone(package.data_directory)
        self.assertIsNone(package.working_directory)

    def test_release_packed_package(self):
        package = self.packed_package
        self.assertFalse(package.is_released())

        package.release()

        self.assertTrue(package.is_released())

    def test_release_after_unpack(self):
        package = self.packed_package
        package.unpack()

        self.assertIsNotNone(package.data_directory)

        package.release()

        self.assertTrue(package.is_released())
        self.assertIsNone(package.data_directory)

    def test_release_clears_working_directory(self):
        package = self.unpacked_package
        work_dir = File("/tmp/test_work")
        package.working_directory = work_dir

        package.release()

        self.assertIsNone(package.working_directory)
        self.assertTrue(package.is_released())

    def test_is_released_initially_false(self):
        package = self.unpacked_package
        self.assertFalse(package.is_released())

    def test_release_multiple_times(self):
        package = self.unpacked_package
        package.release()
        self.assertTrue(package.is_released())

        package.release()
        self.assertTrue(package.is_released())

    def test_pack_unpack_cycle(self):
        package = self.unpacked_package
        self.assertEqual(package.state, Package.State.UNPACKED)

        package.pack()
        self.assertEqual(package.state, Package.State.PACKED)

        packed_data = package.get_bytes()

        new_package = Package(packed_data)
        self.assertEqual(new_package.state, Package.State.PACKED)

        new_package.unpack()
        self.assertEqual(new_package.state, Package.State.UNPACKED)
        self.assertIsNotNone(new_package.data_directory)

    def test_pack_with_custom_metadata_cycle(self):
        resource = self.unpacked_package_resource
        package = Package(resource)

        package.metadata.version = 2
        package.metadata.datadir = "custom_data"
        package.metadata.purpose = "integration test"
        package.metadata.user = "test_user"

        package.pack()
        packed_data = package.get_bytes()

        new_package = Package(packed_data)
        new_package.unpack()

        self.assertEqual(new_package.metadata.version, 2)
        self.assertEqual(new_package.metadata.datadir, "custom_data")
        self.assertEqual(new_package.metadata.purpose, "integration test")
        self.assertEqual(new_package.metadata.user, "test_user")

    def test_multiple_pack_operations_fail(self):
        package = self.unpacked_package
        package.pack()

        with self.assertRaises(PackageOperationException):
            package.pack()

    def test_multiple_unpack_operations_fail(self):
        package = self.packed_package
        package.unpack()

        with self.assertRaises(PackageOperationException):
            package.unpack()

    def test_pack_resets_released_flag(self):
        package = self.unpacked_package
        package.release()
        self.assertTrue(package.is_released())

        new_package = Package(self.unpacked_package_resource)
        new_package.pack()

        self.assertFalse(new_package.is_released())

    def test_unpack_resets_released_flag(self):
        package = self.packed_package
        package.release()
        self.assertTrue(package.is_released())

        new_package = self.packed_package
        new_package.unpack()

        self.assertFalse(new_package.is_released())

    def test_metadata_file_name_constant(self):
        self.assertEqual(Package.METADATA_FILE_NAME, "fathom_meta")

    def test_pack_creates_metadata_file(self):
        package = self.unpacked_package
        package.metadata.purpose = "test metadata"

        package.pack()

        self.assertEqual(package.state, Package.State.PACKED)

    def test_unpack_reads_metadata_file(self):
        resource = self.unpacked_package_resource
        package = Package(resource)
        package.metadata.purpose = "metadata test"
        package.metadata.user = "metadata_user"
        package.pack()

        packed_data = package.get_bytes()
        new_package = Package(packed_data)
        new_package.unpack()

        self.assertEqual(new_package.metadata.purpose, "metadata test")
        self.assertEqual(new_package.metadata.user, "metadata_user")

    def test_pack_files_in_resource_collection(self):
        resource = self.unpacked_package_resource
        package = Package(resource)

        package.pack()

        self.assertEqual(package.state, Package.State.PACKED)
        packed_data = package.get_bytes()
        self.assertGreater(len(packed_data), 0)

    def test_unpack_files_accessible(self):
        package = self.packed_package
        package.unpack()

        data_dir = package.data_directory
        assert data_dir is not None
        file_1 = data_dir / File("file_1")
        self.assertTrue(file_1.exists())

        content_1 = file_1.read_all_text()
        self.assertEqual(content_1, "Data of file_1")

    def test_pack_multiple_files(self):
        resource = self.unpacked_package_resource
        resource.add_bytes("file_3", b"Additional data")
        resource.add_bytes("file_4", b"More data")

        package = Package(resource)
        package.pack()

        self.assertEqual(package.state, Package.State.PACKED)

    def test_pack_unpack_preserves_file_data(self):
        resource = self.unpacked_package_resource
        package = Package(resource)
        package.pack()

        packed_data = package.get_bytes()
        new_package = Package(packed_data)
        new_package.unpack()

        data_dir = new_package.data_directory
        assert data_dir is not None
        file_2 = data_dir / File("file_2")
        self.assertTrue(file_2.exists())

        content_2 = file_2.read_all_text()
        self.assertEqual(content_2, "Data of file_2")


if __name__ == "__main__":
    TestCase.run_tests()
