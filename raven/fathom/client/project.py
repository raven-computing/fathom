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
"""Implements a function to retrieve project details."""

from raven.fathom.base import Project, ProjectVersion
from raven.fathom.base import Configuration
from raven.fathom.base import SystemEnvironment, File
from raven.fathom.client.config import ProjectConfiguration


def _gather_from_project_configuration(config: Configuration):
    project_id = config[ProjectConfiguration.PROJECT.IDENTIFIER]
    project = Project(project_id or "")
    project.name = config[ProjectConfiguration.PROJECT.NAME] or ""
    project.description = (
        config[ProjectConfiguration.PROJECT.DESCRIPTION] or ""
    )
    version = config[ProjectConfiguration.PROJECT.VERSION] or ""
    if version:
        project.version = ProjectVersion(version)

    project.domain = config[ProjectConfiguration.PROJECT.DOMAIN] or ""
    assets = config[ProjectConfiguration.PROJECT.ASSETS] or ""
    if assets and not File(assets).path.is_absolute():
        cwd = SystemEnvironment.instance().get_current_working_directory()
        assets = str(cwd / assets)

    project.assets = assets
    return project


def load_client_project(
    config: Configuration
) -> Project:
    """Retrieves the client project details.

    Args:
        config (Configuration): The project configuration. May be empty.

    Returns:
        Project: The loaded project details.

    Raises:
        MalformedConfigurationValueException: If the project configuration
            is malformed or missing required values.
    """
    project = _gather_from_project_configuration(config)
    return project
