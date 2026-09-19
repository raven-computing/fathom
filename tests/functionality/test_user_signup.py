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
"""Functionality tests for user sign-up commands."""

from raven.fathom.base import File
from raven.fathom.client.config import UserConfiguration

from tests.functionality import TestCase
from tests.fixtures import ConfigurationFixture, ProjectFixture


class TestClientUserSignup(TestCase, ProjectFixture, ConfigurationFixture):
    """End-to-end tests for user registration through the client CLI."""

    def setUp(self):
        super().setUp()
        self.client.env.cwd /= self.project.identifier
        self.project_build_dir = File(self.client.env.cwd / "build")
        self.set_up_project_files(
            self.project_build_dir
        )
        self.client.set_up_configuration_files(
            self.configuration_user,
            self.configuration_project
        )

    def test_newly_created_user_in_onboarding_state_can_sign_up(self):
        self.client.execute(
            "manage", "user", "create", "new-user", "--name", "A New User"
        )

        self.assertClientSuccess("Should be able to create a new user")

        config = self.configuration_user
        config[UserConfiguration.USER.USERNAME] = "new-user"
        config[UserConfiguration.USER.PASSWORD] = "new-password"
        self.client.save_user_configuration(config)

        self.client.execute("deploy")

        self.assertClientFailure(
            "Deployment should fail for a user in onboarding state"
        )
        self.assertClientStdoutContains("Deployment FAILED")
        self.assertClientStdoutContains(
            "Deployment authorization not granted"
        )
        self.assertClientStdoutContains(
            "Status.INVALID_USER User is invalid or unknown"
        )

        self.client.stdin = ["secret", "new-password", "new-password"]
        self.client.execute("setup", "user", "new-user")

        self.assertClientSuccess(
            "User should be able to complete setup successfully"
        )
        self.assertClientStdoutContains("Initialized user 'new-user'")

        # Should be handles by client CLI admin command instead
        ds = self.server.datastore
        project_id = self.project.identifier
        ds.projects().assign_user_to_project(
            ds.users().find_by_identifier("new-user"), # type: ignore
            ds.projects().find_by_identifier(project_id) # type: ignore
        )

        self.client.execute("deploy")

        self.assertClientSuccess("Deployment should succeed after user setup")


if __name__ == "__main__":
    TestCase.run_tests()
