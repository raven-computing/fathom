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
"""Unit tests for the deployment module."""

from raven.fathom.base import File, FilePermission, FileAccess
from raven.fathom.base import Configuration
from raven.fathom.base import ApplicationContext
from raven.fathom.base import ClientDeploymentIntent
from raven.fathom.server.config import ServerConfiguration
from raven.fathom.server.deployment import DeploymentSite
from raven.fathom.server.deployment import DeploymentExecutor
from raven.fathom.server.deployment import DeploymentManager, DeploymentResult
from raven.fathom.server.deployment import DeploymentExecutionException

from tests.unit import TestFixture
from tests.unit import TestCase
from tests.fixtures import ProjectFixture, StagingAreaFixture, PackageFixture


class TestDeploymentSite(TestCase, TestFixture, ProjectFixture):
    """Unit tests the `DeploymentSite` class."""

    def setUp(self):
        super().setUp()
        self.deployment_directory = File("/testing/deployment")
        self.deployment_directory.create_directory_tree()
        self.config = Configuration()
        self.config.get_section(ServerConfiguration.SERVER).set_value(
            ServerConfiguration.SERVER.DEPLOYMENT_SITE_DIRECTORY,
            self.deployment_directory
        )

    def test_deployment_site_directory_property_absolute(self):
        site = DeploymentSite(self.config)
        self.assertEqual(site.directory.path, self.deployment_directory.path)

    def test_deployment_site_directory_property_relative(self):
        relative_directory = File("deployment-test/targets")
        config = Configuration()
        config.get_section(ServerConfiguration.SERVER).set_value(
            ServerConfiguration.SERVER.DEPLOYMENT_SITE_DIRECTORY,
            relative_directory
        )
        site = DeploymentSite(config)
        self.assertTrue(
            str(site.directory.path).endswith(str(relative_directory))
        )
        self.assertFalse(
            str(site.directory.path).startswith(str(relative_directory))
        )
        work_dir = ApplicationContext.instance().get_working_directory()
        self.assertEqual(
            str(site.directory.path),
            str(work_dir / relative_directory)
        )

    def test_has_file_system_access(self):
        site = DeploymentSite(self.config)
        self.deployment_directory.set_permission(
            FilePermission.of(
                owner=FileAccess.all_access(),
                group=FileAccess.all_access(),
                other=FileAccess.of(readable=True, executable=True)
            )
        )
        self.assertTrue(site.has_file_system_access())

    def test_has_no_file_system_access(self):
        site = DeploymentSite(self.config)
        # Remove write access
        self.deployment_directory.set_permission(
            FilePermission.of(
                owner=FileAccess.of(readable=True, executable=True),
                group=FileAccess.of(readable=True, executable=True),
                other=FileAccess.of(readable=True, executable=True)
            )
        )
        self.assertFalse(site.has_file_system_access())

    def test_get_project_target_directory(self):
        site = DeploymentSite(self.config)
        project = self.project_v1
        assert project.version is not None
        proj_dir = f"{project.identifier}/{project.version.identifier}"
        target_dir = site.get_target_directory(project)
        self.assertIsInstance(target_dir, File)
        self.assertTrue(target_dir.path.as_posix().endswith(proj_dir))

    def test_site_contains_project_directory(self):
        site = DeploymentSite(self.config)
        project = self.project
        assert project.version is not None
        proj_dir = File(project.identifier) / File(project.version.identifier)
        (site.directory / proj_dir).create_directory_tree()
        self.assertTrue(site.contains(project))

    def test_site_does_not_contain_project_directory(self):
        site = DeploymentSite(self.config)
        project = self.project_v1
        assert project.version is not None
        proj_dir = File(project.identifier) / File(project.version.identifier)
        (site.directory / proj_dir).create_directory_tree()
        self.assertFalse(site.contains(self.project_v2))


class TestDeploymentExecutor(
    TestCase, TestFixture, ProjectFixture, StagingAreaFixture, PackageFixture
):
    """Unit tests the `DeploymentExecutor` class."""

    def setUp(self):
        super().setUp()
        self.deployment_directory = File("/testing/deployment")
        self.deployment_directory.create_directory_tree()
        self.config = Configuration()
        self.config.get_section(ServerConfiguration.SERVER).set_value(
            ServerConfiguration.SERVER.DEPLOYMENT_SITE_DIRECTORY,
            self.deployment_directory
        )

    def test_execution_moves_data_from_staging_area_to_deployment_site(self):
        project = self.project
        staging_area = self.staging_area
        staging_area.directory.create_directory_tree()
        staging_area.put(project, self.packed_package)
        deployment_site = DeploymentSite(self.config)
        self.assertTrue(staging_area.contains(project))
        self.assertFalse(deployment_site.contains(project))
        executor = DeploymentExecutor(staging_area, deployment_site)
        executor.deploy(project)
        self.assertFalse(staging_area.contains(project))
        self.assertTrue(deployment_site.contains(project))

    def test_file_io_error_in_execution_raises_deployment_exception(self):
        staging_area = self.staging_area
        staging_area.directory.create_directory_tree()
        executor = DeploymentExecutor(
            staging_area, DeploymentSite(self.config)
        )
        with self.assertRaises(DeploymentExecutionException) as raised:
            executor.deploy(self.project)

        self.assertIn(
            "Failed to move data from staging area to target directory",
            str(raised.exception)
        )


class TestDeploymentManager(
    TestCase, TestFixture, ProjectFixture, PackageFixture
):
    """Unit tests the `DeploymentManager` class."""

    def setUp(self):
        super().setUp()
        self.staging_area_directory = File("/testing/staging")
        self.staging_area_directory.create_directory_tree()
        self.deployment_directory = File("/testing/deployment")
        self.deployment_directory.create_directory_tree()
        self.config = Configuration()
        self.config.get_section(ServerConfiguration.SERVER).set_value(
            ServerConfiguration.SERVER.DEPLOYMENT_STAGING_DIRECTORY,
            self.staging_area_directory
        )
        self.config.get_section(ServerConfiguration.SERVER).set_value(
            ServerConfiguration.SERVER.DEPLOYMENT_SITE_DIRECTORY,
            self.deployment_directory
        )
        self.intent = ClientDeploymentIntent()
        self.intent.project = self.project

    def test_deploy_package_with_valid_intent(self):
        manager = DeploymentManager(self.config)
        result = manager.deploy(self.intent, self.packed_package)
        self.assertIsInstance(result, DeploymentResult)
        self.assertTrue(result.successful)
        self.assertIn("Successfully deployed package", result.user_message)

    def test_deploy_is_rejected_when_target_exists_and_overwrite_false(self):
        self.intent.overwrite_existing = False
        assert self.intent.project is not None
        DeploymentSite(self.config).get_target_directory(
            self.intent.project
        ).create_directory_tree()
        manager = DeploymentManager(self.config)
        result = manager.deploy(self.intent, self.packed_package)
        self.assertIsInstance(result, DeploymentResult)
        self.assertFalse(result.successful)
        self.assertIn("Cannot deploy project", result.user_message)
        self.assertIn(
            "as it is already deployed and the 'overwrite existing' "
            "setting was disabled or not authorized",
            result.user_message
        )


if __name__ == "__main__":
    TestCase.run_tests()
