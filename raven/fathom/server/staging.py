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
"""Management of the deployment staging area.

A staging area is a filesystem directory where packages submitted for
deployment are unpacked and prepared for the final deployment. It is a
temporary storage area in a non-temporary filesystem location, under the
application's working directory, that allows for the safe handling of
deployment artifacts before they are moved to their final destination.
A staging area can hold multiple staging spots, each of which is a dedicated
subdirectory that is managed by the staging area for one specific project.
Each staging spot is uniquely identified by the combination of the project
identifier and the project version identifier.
"""

from raven.fathom.base import ApplicationContext, Configuration
from raven.fathom.base import Project, Package
from raven.fathom.base import File, FileIOException, FileNotFoundException
from raven.fathom.base import FileLockAcquisitionException
from raven.fathom.base import PackageOperationException
from raven.fathom.server.dao import DataAccess, DatastoreException
from raven.fathom.server.config import ServerConfiguration
from raven.fathom.server.models import StagingAllocation
from raven.fathom.server.exceptions import FathomServerException


class StagingAreaException(FathomServerException):
    """Something is wrong with the staging area."""


class InvalidStagingSpotException(StagingAreaException):
    """An attempt was made to operate on a staging spot that is invalid."""


class StagingSpotLockedException(StagingAreaException):
    """The staging spot is locked and cannot be accessed."""


class UnpackException(StagingAreaException):
    """The unpacking of a deployment package failed."""


class StagingSpot:
    """A concrete place within a staging area for a specific project.

    Attributes:
        relative_path (File): The relative path of the staging spot within the
            staging area, based on the project identifier and version.
        project_directory (File): The directory for the project within the
            staging area, which may contain multiple versions of the project.
        directory (File): The specific directory for the staging spot, which is
            unique to the project identifier and version.
    """

    def __init__(self, staging_area_root: File, project: Project):
        """Initialize a staging spot for a specific project.

        Args:
            staging_area_root (File): The root directory of the staging area.
                Must be a valid directory in the filesystem and the `File`
                object must have an absolute path.
            project (Project): The project for which this staging spot
                is allocated. Must have a valid version identifier.
        
        Raises:
            InvalidStagingSpotException: If the `staging_area_root` is not a
                valid directory or does not have an absolute path or
                the `project` does not have a valid version identifier.
        """
        if not staging_area_root.path.is_absolute():
            raise InvalidStagingSpotException(
                "Staging area root must be an absolute path: "
                f"'{staging_area_root}'"
            )

        if not staging_area_root.is_directory():
            raise InvalidStagingSpotException(
                "Staging area root must be an existing directory: "
                f"'{staging_area_root}'"
            )

        if project.version is None or not project.version.identifier:
            raise InvalidStagingSpotException(
                "Project version must be specified and have an identifier: "
                f"'{project}'"
            )

        self.relative_path = File(
            f"{project.identifier}/{project.version.identifier}"
        )
        self.project_directory = staging_area_root / project.identifier
        self.directory = (
            staging_area_root / self.relative_path
        )
        self.project = project

    def lock(self):
        """Locks this staging spot.

        Raises:
            StagingSpotLockedException: If the staging spot is already locked.
            StagingAreaException: If there is an I/O error while attempting
                to lock this spot.
        """
        if not self.is_locked():
            try:
                self.project_directory.lock()
            except FileLockAcquisitionException as ex:
                raise StagingSpotLockedException(
                    "Staging spot already in use (locked): "
                    f"'{self.project_directory}'"
                ) from ex
            except FileIOException as ex:
                raise StagingAreaException(
                    f"Failed to lock staging spot: '{self.project_directory}'"
                ) from ex

    def unlock(self):
        """Unlocks this staging spot.

        Raises:
            StagingAreaException: If there is an I/O error while attempting
                to unlock this spot.
        """
        if self.is_locked():
            try:
                self.project_directory.unlock()
            except FileIOException as ex:
                raise StagingAreaException(
                    f"Failed to unlock staging spot: '{self.directory}'"
                ) from ex

    def is_locked(self) -> bool:
        """Indicates whether this staging spot is currently locked.
        
        Returns:
            bool: `True` if the staging spot is currently locked,
                `False` otherwise.
        """
        return self.project_directory.is_locked()

    def is_allocated(self) -> bool:
        """Indicates whether this staging spot is already allocated.

        Returns:
            bool: `True` if the staging spot is currently allocated
                in persistent storage, `False` otherwise.
        """
        return self.directory.is_directory()

    def allocate(self):
        """Allocates this staging spot in persistent storage.

        This creates the necessary directory structure.

        Raises:
            StagingAreaException: If the staging spot is already allocated or
                if there is an I/O error while attempting to create
                the directory structure.
        """
        if self.is_allocated():
            raise StagingAreaException(
                "Staging spot already in use "
                f"for {self.project}: '{self.directory}'"
            )

        try:
            self.directory.create_directory_tree()
        except FileIOException as ex:
            raise StagingAreaException(
                f"Failed to create staging spot: '{self.directory}'"
            ) from ex

    def deallocate(self) -> bool:
        """Deallocates this staging spot from persistent storage.

        Returns:
            bool: `True` if the staging spot was previously allocated and
                has been successfully deallocated, `False` if no deallocation
                was necessary.

        Raises:
            StagingAreaException: If there is an I/O error while attempting
                to remove the directory structure.
        """
        alloc_removed = False
        try:
            if self.is_allocated():
                self.directory.remove()
                alloc_removed = True

            if self.project_directory.is_empty():
                self.project_directory.remove()
                # This has also removed the lock file for above directory

            return alloc_removed
        except FileNotFoundException:
            return alloc_removed
        except FileIOException as ex:
            raise StagingAreaException(
                f"Failed to deallocate staging spot: '{self.directory}'"
            ) from ex

    def __enter__(self):
        self.lock()
        return self

    def __exit__(self, ex_type, ex_value, ex_trace):
        try:
            self.unlock()
        except StagingAreaException as unlock_exception:
            if ex_type is None:
                raise unlock_exception


class Unpacker:
    """Unpacks a deployment package in a staging area to make
    it ready for deployment.
    """

    def __init__(self, staging_spot: StagingSpot, package: Package):
        """Initializes an `Unpacker` to work on the given staging spot
        and a deployment package.

        Args:
            staging_spot (StagingSpot): The staging spot where the package
                will be unpacked.
            package (Package): The deployment package to be unpacked.
        """
        self._staging_spot = staging_spot
        self._package = package

    def unpack(self) -> File:
        """Unpacks the deployment package into the staging spot.

        Returns:
            File: The directory where the package was unpacked.
                This is the data directory of the unpacked package.

        Raises:
            UnpackException: If the unpacking of the package fails or if
                the data directory is not set up after unpacking.
        """
        data_directory = None
        try:
            self._package.working_directory = (
                self._staging_spot.project_directory
            )
            self._package.unpack()
            data_directory = self._package.data_directory
        except PackageOperationException as ex:
            raise UnpackException("Failed to unpack data package") from ex

        if data_directory is None:
            raise UnpackException(
                "Data directory is not set up correctly "
                "after unpacking package"
            )

        return data_directory


class StagingArea:
    """The Fathom server deployment staging area.
    
    Attributes:
        directory (File): The root directory of the staging area within the
            filesystem.
    """

    def __init__(self, config: Configuration):
        """Initializes the staging area with the given configuration.

        Args:
            config (Configuration): The configuration object containing
                settings for the staging area, including the root directory
                path.

        Raises:
            StagingAreaException: If the root directory cannot be determined.
        """
        self._config = config
        self._ds = DataAccess.instance()
        self._root_dir = self._determine_root_directory()

    @property
    def directory(self) -> File:
        """The root directory of the staging area within the filesystem.

        Returns:
            File: A `File` referring to the staging area root directory.
        """
        return File(self._root_dir)

    def create(self):
        """Creates the staging area directory if it does not exist.

        Raises:
            StagingAreaException: If the staging area cannot be created.
        """
        staging_directory = self._root_dir
        if staging_directory.exists():
            self._check_fs_state_for_existing(staging_directory)
        else:
            try:
                staging_directory.create_directory_tree()
            except FileIOException as ex:
                raise StagingAreaException(
                    "Failed to set up staging area. "
                    "A file I/O error has occurred while trying "
                    "to create the staging area directory tree"
                ) from ex

    def contains(self, project: Project) -> bool:
        """Indicates whether the staging area contains a staging
        spot for the given project.

        Args:
            project (Project): The project to check for in the staging area.
                Must have a valid version identifier.

        Returns:
            bool: `True` if a staging spot for the project exists in the
                staging area, `False` otherwise.
        """
        return StagingSpot(self._root_dir, project).is_allocated()

    def put(self, project: Project, package: Package):
        """Inserts a package into the staging area for the given project.

        Args:
            project (Project): The project for which the package is being
                staged. Must have a valid version identifier.
            package (Package): The package to be staged. Must be in
                a packed state.

        Raises:
            StagingAreaException: If there is an error during the staging
                process, such as I/O errors, unpacking failures, or if the
                staging spot is already allocated.
        """
        with StagingSpot(self._root_dir, project) as staging_spot:
            try:
                staging_spot.allocate()
                Unpacker(staging_spot, package).unpack().move(
                    staging_spot.directory
                )
                package.release()
                self._save_allocation(staging_spot)
            except (
                FileIOException,
                PackageOperationException,
                UnpackException,
                DatastoreException
            ) as ex:
                staging_spot.deallocate()
                raise StagingAreaException(
                    "Failed to stage package for deployment "
                    f"for project '{project}'"
                ) from ex

    def remove(self, project: Project) -> bool:
        """Removes the staging spot for the given project
        from this staging area.

        Returns:
            bool: `True` if the staging spot was deallocated,
                `False` if no deallocation was necessary
                (i.e. the staging spot did not exist).

        Raises:
            StagingAreaException: If an error occurs while attempting
                to remove the staging spot.
        """
        with StagingSpot(self._root_dir, project) as staging_spot:
            was_deallocated = staging_spot.deallocate()
            self._remove_allocation(staging_spot)
            return was_deallocated

    def get_project_directory(self, project: Project) -> File:
        """Gets the directory for the given project within the staging area.

        This is the parent directory that may contain multiple versions
        of the project.

        Args:
            project (Project): The project for which to get the directory.
                Must have a valid version identifier.

        Returns:
            File: The project directory with an absolute path.

        Raises:
            InvalidStagingSpotException: If the staging spot cannot
                be initialized.
        """
        return StagingSpot(self._root_dir, project).project_directory

    def get_allocation_directory(self, project: Project) -> File:
        """Gets the directory for the specific staging spot that may be
        allocated for the given project in that specific version.

        Args:
            project (Project): The project for which to get the
                allocation directory. Must have a valid version identifier.

        Returns:
            File: The allocation directory with an absolute path.

        Raises:
            InvalidStagingSpotException: If the staging spot cannot
                be initialized.
        """
        return StagingSpot(self._root_dir, project).directory

    def _check_fs_state_for_existing(self, staging_directory: File):
        if not staging_directory.is_directory():
            raise StagingAreaException(
                "Staging area cannot be created because a file at "
                "that path already exists but "
                f"is not a directory: '{staging_directory}'"
            )

        if not staging_directory.is_writable():
            raise StagingAreaException(
                "Staging area cannot be created "
                "because a directory at that path already exists but "
                f"is not writable: '{staging_directory}'"
            )

    def _save_allocation(self, staging_spot):
        project = staging_spot.project
        project_dao = self._ds.projects()
        project_version = project_dao.find_version_by_identifier(
            project.identifier, project.version.identifier
        )
        if project_version is None:
            raise StagingAreaException(
                "Cannot save staging allocation: Project record not found"
            )

        project_dao.create(
            StagingAllocation(
                project_version=project_version,
                path=str(staging_spot.relative_path),
            )
        )

    def _remove_allocation(self, staging_spot):
        project = staging_spot.project
        project_version = self._ds.projects().find_version_by_identifier(
            project.identifier, project.version.identifier
        )
        if project_version is not None:
            self._ds.projects().delete_staging_allocation(project_version)

    def _determine_root_directory(self):
        staging_directory = self._config.get_required_value(
            ServerConfiguration.SERVER.DEPLOYMENT_STAGING_DIRECTORY,
            or_raise=StagingAreaException
        )

        if not staging_directory.path.is_absolute():
            root_base = self._get_default_root_base_directory()
            return root_base / staging_directory

        return staging_directory

    def _get_default_root_base_directory(self):
        ctx = ApplicationContext.instance()
        return ctx.get_working_directory()
