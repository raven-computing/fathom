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
"""Unit tests for the deployment staging area."""

from raven.fathom.base import File, FilePermission, FileAccess
from raven.fathom.base import Package
from raven.fathom.server.config import ServerConfiguration
from raven.fathom.server.models import ProjectVersion, StagingAllocation
from raven.fathom.server.staging import StagingArea, StagingSpot
from raven.fathom.server.staging import StagingAreaException
from raven.fathom.server.staging import InvalidStagingSpotException
from raven.fathom.server.staging import Unpacker, UnpackException

from tests.unit import TestFixture
from tests.unit import TestCase
from tests.unit.server.mocks import DataAccessMock
from tests.fixtures import StagingAreaFixture, ProjectFixture, PackageFixture


class TestStagingSpot(TestCase, TestFixture, ProjectFixture):
    """Unit tests for the internal `StagingSpot` class."""

    def setUp(self):
        super().setUp()
        self.staging_spot_root = File("/testing/staging")
        self.staging_spot_root.create_directory_tree()

    def test_staging_spot_property_types(self):
        project = self.project
        staging_dir = File("/testing/directory")
        staging_dir.create_directory_tree()
        spot = StagingSpot(staging_dir, project)
        self.assertIsInstance(spot.relative_path, File)
        self.assertIsInstance(spot.project_directory, File)
        self.assertIsInstance(spot.directory, File)
        self.assertIs(spot.project, project)

    def test_staging_spot_with_relative_root_raises_exception(self):
        relative_dir = File("testing/relative")
        with self.assertRaises(InvalidStagingSpotException) as raised:
            StagingSpot(relative_dir, self.project)

        self.assertIn("must be an absolute path", str(raised.exception))

    def test_staging_spot_with_nonexistent_root_raises_exception(self):
        nonexistent_dir = File("/testing/nonexistent_root")
        with self.assertRaises(InvalidStagingSpotException) as raised:
            StagingSpot(nonexistent_dir, self.project)

        self.assertIn("must be an existing directory", str(raised.exception))

    def test_staging_spot_with_missing_project_version_raises_exception(self):
        project_no_version = self.project
        project_no_version.version = None
        with self.assertRaises(InvalidStagingSpotException) as raised:
            StagingSpot(self.staging_spot_root, project_no_version)

        self.assertIn(
            "Project version must be specified",
            str(raised.exception)
        )

    def test_staging_spot_can_be_locked_when_free(self):
        project = self.project
        spot_1 = StagingSpot(self.staging_spot_root, project)
        spot_2 = StagingSpot(self.staging_spot_root, project)
        spot_2.lock()
        self.assertFalse(spot_1.is_locked())
        self.assertTrue(spot_2.is_locked())
        spot_2.unlock()
        self.assertFalse(spot_1.is_locked())
        self.assertFalse(spot_2.is_locked())

    def test_staging_spot_cannot_be_locked_when_already_locked(self):
        spot_1 = StagingSpot(self.staging_spot_root, self.project)
        spot_2 = StagingSpot(self.staging_spot_root, self.project)
        spot_1.lock()
        self.assertTrue(spot_1.is_locked())
        self.assertFalse(spot_2.is_locked())
        with self.assertRaises(StagingAreaException) as raised:
            spot_2.lock()

        self.assertIn(
            "Staging spot already in use (locked)", str(raised.exception)
        )
        self.assertTrue(spot_1.is_locked())
        self.assertFalse(spot_2.is_locked())
        spot_1.unlock()
        self.assertFalse(spot_1.is_locked())
        self.assertFalse(spot_2.is_locked())

    def test_spot_cannot_be_locked_when_already_locked_by_diff_version(self):
        spot_1 = StagingSpot(self.staging_spot_root, self.project_v1)
        spot_2 = StagingSpot(self.staging_spot_root, self.project_v2)
        spot_1.lock()
        self.assertTrue(spot_1.is_locked())
        self.assertFalse(spot_2.is_locked())
        with self.assertRaises(StagingAreaException) as raised:
            spot_2.lock()

        self.assertIn(
            "Staging spot already in use (locked)", str(raised.exception)
        )
        self.assertTrue(spot_1.is_locked())
        self.assertFalse(spot_2.is_locked())
        spot_1.unlock()
        self.assertFalse(spot_1.is_locked())
        self.assertFalse(spot_2.is_locked())

    def test_spots_can_be_locked_for_different_projects_simultaneously(self):
        project_1 = self.project
        project_2 = self.project
        project_2.identifier = "test-project-2"
        project_2.name = "Test-Project-2"
        spot_project_1 = StagingSpot(self.staging_spot_root, project_1)
        spot_project_2 = StagingSpot(self.staging_spot_root, project_2)
        spot_project_1.lock()
        spot_project_2.lock()
        self.assertTrue(spot_project_1.is_locked())
        self.assertTrue(spot_project_2.is_locked())
        spot_project_1.unlock()
        spot_project_2.unlock()
        self.assertFalse(spot_project_1.is_locked())
        self.assertFalse(spot_project_2.is_locked())

    def test_context_manager_locks_and_unlocks_spots(self):
        spot = StagingSpot(self.staging_spot_root, self.project)
        self.assertFalse(spot.is_locked())
        with spot as ctx:
            self.assertIs(spot, ctx)
            self.assertTrue(spot.is_locked())

        self.assertFalse(spot.is_locked())


class TestUnpacker(TestCase, TestFixture, ProjectFixture, PackageFixture):
    """Unit tests for the internal `Unpacker` class."""

    def setUp(self):
        super().setUp()
        staging_spot_root = File("/testing/staging")
        staging_spot_root.create_directory_tree()
        self.staging_spot = StagingSpot(staging_spot_root, self.project)

    def test_unpacking_of_package_in_unpacked_state_raises_exception(self):
        unpacker = Unpacker(self.staging_spot, self.unpacked_package)
        with self.assertRaises(UnpackException) as raised:
            unpacker.unpack()

        self.assertIn("Failed to unpack data", str(raised.exception))

    def test_unpacking_in_nonexisting_project_staging_dir_raises_ex(self):
        unpacker = Unpacker(self.staging_spot, self.packed_package)
        with self.assertRaises(UnpackException) as raised:
            unpacker.unpack()

        self.assertIn("Failed to unpack data", str(raised.exception))

    def test_unpacking_of_package_in_staging_directory(self):
        self.staging_spot.project_directory.create_directory_tree()
        unpacker = Unpacker(self.staging_spot, self.packed_package)
        unpacked_data_directory = unpacker.unpack()
        self.assertIsInstance(unpacked_data_directory, File)
        expected_unpacked_data_directory = File(
            self.staging_spot.project_directory / "pkge_0/data"
        )
        self.assertEqual(
            str(unpacked_data_directory),
            str(expected_unpacked_data_directory)
        )
        package_metadata_file = File(
            self.staging_spot.project_directory / "pkge_0/fathom_meta"
        )
        self.assertTrue(package_metadata_file.is_regular_file())


class TestStagingArea(
    TestCase, TestFixture, StagingAreaFixture, ProjectFixture, PackageFixture
):
    """Unit tests for the `StagingArea` class."""

    def setUp(self):
        super().setUp()
        DataAccessMock.reset()
        self.expected_staging_area_directory = (
            self.app_context.get_working_directory()
            / self.staging_area_config.get_section(
                ServerConfiguration.SERVER,
            ).value_of(ServerConfiguration.SERVER.DEPLOYMENT_STAGING_DIRECTORY)
        )

    def assert_allocation_exists(self, staging_area, project):
        """Asserts that the staging area has an allocation in the filesystem
        for the given project.
        """
        spot = StagingSpot(staging_area.directory, project)
        path_of_allocation = staging_area.directory / spot.relative_path
        self.assertTrue(path_of_allocation.is_directory())
        self.assertTrue(
            staging_area.get_allocation_directory(project).is_directory()
        )
        self.assertTrue(
            staging_area.get_project_directory(project).is_directory()
        )

    def assert_allocation_was_removed(self, staging_area, project):
        """Asserts that the staging area does not have a corresponding
        allocation in the filesystem for the given project and the DAO methods
        for removing a staging allocation were used correctly.
        """
        self.assertFalse(
            staging_area.get_allocation_directory(project).exists()
        )
        spot = StagingSpot(staging_area.directory, project)
        path_of_allocation = staging_area.directory / spot.relative_path
        self.assertFalse(path_of_allocation.exists())
        dao = DataAccessMock().projects()
        self.assertEqual(
            dao.find_version_by_identifier.call_args.args[0],
            project.identifier
        )
        self.assertEqual(
            dao.find_version_by_identifier.call_args.args[1],
            project.version.identifier
        )
        self.assertEqual(
            dao.delete_staging_allocation.call_args.args[0].version_identifier,
            project.version.identifier
        )

    def put_package_into(self, staging_area, project):
        """Inserts a package for the given project into
        the given staging area and returns the corresponding
        saved `StagingAllocation` record.
        """
        ds = DataAccessMock()
        staging_area.create()
        project_version = ProjectVersion(
            project=1,
            version_sequence=1,
            version_identifier=project.version.identifier
        )
        ds.projects().find_version_by_identifier.return_value = project_version
        staging_area.put(project, self.packed_package)
        allocation = ds.data(StagingAllocation).create.call_args.args[0]
        self.assertIsInstance(allocation, StagingAllocation)
        return allocation

    def test_staging_area_directory_prop(self):
        self.assertIsInstance(self.staging_area.directory, File)
        self.assertEqual(
            self.staging_area.directory,
            self.expected_staging_area_directory
        )

    def test_can_create_new_staging_area(self):
        self.staging_area.create()
        self.assertTrue(self.staging_area.directory.is_directory())
        self.assertTrue(self.staging_area.directory.is_empty())
        self.assertEqual(
            str(self.staging_area.directory.path),
            str(self.expected_staging_area_directory)
        )

    def test_can_create_new_staging_area_with_arbitrary_root_path(self):
        config = self.staging_area_config
        staging_area_path = "/opt/apps/fathom/staging/test"
        config[ServerConfiguration.SERVER].set_value( # type: ignore
            ServerConfiguration.SERVER.DEPLOYMENT_STAGING_DIRECTORY,
            staging_area_path
        )
        staging_area = StagingArea(config)
        staging_area.create()
        self.assertTrue(staging_area.directory.is_directory())
        self.assertTrue(staging_area.directory.is_empty())
        staging_area_directory = staging_area.directory.path.as_posix()
        self.assertTrue(staging_area_directory.endswith(staging_area_path))

    def test_creating_new_staging_area_at_nonwritable_path_raises_ex(self):
        # Remove write perms from a parent dir of the staging root dir
        self.app_context.get_working_directory().set_permission(
            FilePermission.of(owner=FileAccess.of(readable=True))
        )
        with self.assertRaises(StagingAreaException) as raised:
            self.staging_area.create()

        self.assertIn(
            "Failed to set up staging area",
            str(raised.exception)
        )
        self.assertIn(
            "A file I/O error has occurred while trying "
            "to create the staging area directory tree",
            str(raised.exception)
        )

    def test_can_create_new_staging_area_when_root_path_already_exists(self):
        self.staging_area.directory.create_directory_tree()
        self.staging_area.create()
        self.assertTrue(self.staging_area.directory.is_directory())
        self.assertTrue(self.staging_area.directory.is_empty())

    def test_creating_new_staging_area_when_root_path_is_reg_file_raises(self):
        self.staging_area.directory.create()
        with self.assertRaises(StagingAreaException) as raised:
            self.staging_area.create()

        self.assertIn(
            "Staging area cannot be created because a file at that "
            "path already exists but is not a directory",
            str(raised.exception)
        )
        self.assertTrue(self.staging_area.directory.is_regular_file())

    def test_create_new_stag_area_in_existing_nonwritable_root_raises_ex(self):
        self.staging_area.directory.create_directory_tree()
        # Remove write perms for staging root dir
        self.staging_area.directory.set_permission(
            FilePermission.of(owner=FileAccess.of(readable=True))
        )
        with self.assertRaises(StagingAreaException) as raised:
            self.staging_area.create()

        self.assertIn(
            "Staging area cannot be created because a directory "
            "at that path already exists but is not writable",
            str(raised.exception)
        )

    def test_put_project_package_into_staging_area(self):
        project = self.project
        staging_area = self.staging_area
        allocation_record = self.put_package_into(staging_area, project)
        assert project.version is not None
        self.assertEqual(
            allocation_record.project_version.version_identifier,
            project.version.identifier
        )
        self.assert_allocation_exists(staging_area, project)
        self.assertTrue(staging_area.contains(project))
        staging_area_content = list(staging_area.directory.list_files())
        self.assertEqual(len(staging_area_content), 1)
        self.assertTrue(staging_area_content[0].is_directory())

    def test_package_is_unpacked_when_put_into_staging_area(self):
        staging_area = self.staging_area
        packed_package = self.packed_package
        staging_area.create()
        staging_area.put(self.project, packed_package)
        self.assertEqual(packed_package.state, Package.State.UNPACKED)
        self.assertTrue(packed_package.is_released())

    def test_staging_area_contains_put_project_package(self):
        staging_area = self.staging_area
        staging_area.create()
        self.assertFalse(staging_area.contains(self.project))
        staging_area.put(self.project, self.packed_package)
        self.assertTrue(staging_area.contains(self.project))
        different_version_of_project = self.project_v1_patched
        self.assertFalse(staging_area.contains(different_version_of_project))

    def test_get_project_directory(self):
        staging_area = self.staging_area
        staging_area.directory.create_directory_tree()
        project_directory = staging_area.get_project_directory(self.project)
        self.assertTrue(
            str(project_directory.path).startswith(
                str(self.app_context.get_working_directory())
            )
        )
        self.assertTrue(
            project_directory.path.is_relative_to(staging_area.directory.path)
        )
        self.assertIn(self.project.identifier, project_directory.name)

    def test_get_allocation_directory(self):
        staging_area = self.staging_area
        staging_area.directory.create_directory_tree()
        allocation_dir = staging_area.get_allocation_directory(self.project)
        self.assertTrue(
            str(allocation_dir.path).startswith(
                str(self.app_context.get_working_directory())
            )
        )
        self.assertTrue(
            allocation_dir.path.is_relative_to(
                staging_area.get_project_directory(self.project).path
            )
        )
        self.assertIn(
            self.project.identifier,
            allocation_dir.get_parent_directory().name
        )
        assert self.project.version is not None
        self.assertIn(self.project.version.identifier, allocation_dir.name)

    def test_remove_existing_project_package_from_staging_area(self):
        staging_area = self.staging_area
        project = self.project
        allocation_record = self.put_package_into(staging_area, project)
        full_path_of_staging_data = (
            staging_area.directory / allocation_record.path
        )
        was_removed = staging_area.remove(project)
        self.assertTrue(was_removed)
        self.assert_allocation_was_removed(staging_area, project)
        self.assertFalse(full_path_of_staging_data.exists())
        self.assertFalse(staging_area.get_project_directory(project).exists())

    def test_remove_nonexisting_project_package_from_staging_area(self):
        dao = DataAccessMock().projects()
        staging_area = self.staging_area
        existing_project = self.project
        nonexisting_project = self.project
        nonexisting_project.identifier = "test-project-2"
        self.put_package_into(staging_area, existing_project)
        dao.find_version_by_identifier.reset_mock()
        was_removed = staging_area.remove(nonexisting_project)
        self.assertFalse(was_removed)
        dao.find_version_by_identifier.assert_called_once()
        dao.delete_staging_allocation.assert_called_once()
        self.assert_allocation_exists(staging_area, existing_project)
        self.assert_allocation_was_removed(staging_area, nonexisting_project)

    def test_remove_nonexisting_project_when_other_version_exists(self):
        dao = DataAccessMock().projects()
        staging_area = self.staging_area
        existing_project = self.project_v1
        nonexisting_project = self.project_v2
        self.put_package_into(staging_area, existing_project)
        dao.find_version_by_identifier.reset_mock()
        assert nonexisting_project.version is not None
        dao.find_version_by_identifier.return_value = ProjectVersion(
            project=1,
            version_sequence=2,
            version_identifier=nonexisting_project.version.identifier,
        )
        was_removed = staging_area.remove(nonexisting_project)
        self.assertFalse(was_removed)
        dao.find_version_by_identifier.assert_called_once()
        dao.delete_staging_allocation.assert_called_once()
        self.assert_allocation_exists(staging_area, existing_project)
        self.assert_allocation_was_removed(staging_area, nonexisting_project)

    def test_remove_pack_from_staging_area_which_contains_other_version(self):
        staging_area = self.staging_area
        project_v1 = self.project_v1
        project_v2 = self.project_v2
        self.put_package_into(staging_area, project_v1)
        self.put_package_into(staging_area, project_v2)
        v2_was_removed = staging_area.remove(project_v2)
        self.assertTrue(v2_was_removed)
        self.assert_allocation_was_removed(staging_area, project_v2)
        self.assert_allocation_exists(staging_area, project_v1)


if __name__ == "__main__":
    TestCase.run_tests()
