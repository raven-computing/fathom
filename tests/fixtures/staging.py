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
"""Test fixtures for deployment staging areas."""

from raven.fathom.base import Configuration
from raven.fathom.server.config import ServerConfiguration
from raven.fathom.server.staging import StagingArea

from tests.common import FathomTestFixture


class StagingAreaConfigurationFixture(FathomTestFixture):
    """Test fixture to set up a deployment staging area configuration."""

    @property
    def staging_area_config(self) -> Configuration:
        """A `Configuration` object as a fixture suitable
        to create `StagingArea` instances.
        """
        config = self.app_config
        server = config.get_section(ServerConfiguration.SERVER)
        server.set_value(
            ServerConfiguration.SERVER.DEPLOYMENT_STAGING_DIRECTORY,
            "deployment/staging"
        )
        return config


class StagingAreaFixture(StagingAreaConfigurationFixture):
    """Test fixture to set up a `StagingArea` instance."""

    @property
    def staging_area(self) -> StagingArea:
        """A `StagingArea` object with `staging_area_config` as
        a default configuration.
        """
        return StagingArea(self.staging_area_config)
