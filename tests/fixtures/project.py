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
"""Test fixtures for project entities."""

from raven.fathom.base import Project, ProjectVersion
from raven.fathom.base import File

from tests.common import FathomTestFixture

# pyright: reportOptionalMemberAccess=false


class ProjectFixture(FathomTestFixture):
    """Test fixture to set up project entities."""

    @property
    def project(self) -> Project:
        """A `Project` object test fixture."""
        project = Project("test-project-1")
        project.name = "Test-Project-1"
        project.description = "A Project for Testing Purposes (1)."
        project.version = ProjectVersion("1.0.0")
        return project

    @property
    def project_v1(self) -> Project:
        """An alias for the `project` property."""
        return self.project

    @property
    def project_v1_patched(self) -> Project:
        """The same project as the `project` property,
        but with an incremented patch version number v1.0.1
        instead of v1.0.0.
        """
        project_v1_patched = self.project
        project_v1_patched.version.identifier = "1.0.1"
        return project_v1_patched

    @property
    def project_v2(self) -> Project:
        """The same project as the `project` property,
        but with version v2.0.0 instead of v1.0.0.
        """
        project_v2 = self.project
        project_v2.version.identifier = "2.0.0"
        return project_v2

    def get_project_resource_directory(self) -> File:
        """Gets the directory that contains the deployable resources
        of the project designated by the `project` property.

        Returns:
            File: The directory containing the deployable resources
                of the project.
        """
        fixture_dir = File(__file__).get_parent_directory()
        return fixture_dir / File("res/projects") / self.project.identifier

    def set_up_project_files(self, target: File):
        """Copies project resource files to the given target location.

        This method can only be used when real interaction with
        the host filesystem is enabled during testing.
        """
        # Source does not exist in virtual FS
        source = self.get_project_resource_directory()
        target.get_parent_directory().create_directory_tree()
        source.copy(target)
