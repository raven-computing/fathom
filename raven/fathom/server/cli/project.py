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
"""CLI command handling for project management actions."""

from raven.fathom.base import Project
from raven.fathom.server.cli.command import require_privileges
from raven.fathom.server.cli.command import ServerCommand
from raven.fathom.server.cli.command import require_database
from raven.fathom.server.logging import Logger
from raven.fathom.server.project_management import ProjectManager


LOG = Logger.get()


class ProjectCreateCommand(ServerCommand):
    """Implementation of `project create`."""

    @require_database
    @require_privileges
    def execute(self) -> int:
        manager = ProjectManager()
        project = Project(
            identifier=self.args.project_identifier,
            name=self.args.project_name,
            description=self.args.project_description,
        )
        manager.create_project(project)
        LOG.i("Created project '%s'.", project.identifier)
        return 0


class ProjectListCommand(ServerCommand):
    """Implementation of `project list`."""

    @require_database
    @require_privileges
    def execute(self) -> int:
        manager = ProjectManager()
        for project in manager.list_projects():
            LOG.i(
                "Project: '%s'\tName: '%s'\tDescription: '%s'",
                project.identifier,
                project.name,
                project.description,
            )
        return 0


class ProjectDeleteCommand(ServerCommand):
    """Implementation of `project delete`."""

    @require_database
    @require_privileges
    def execute(self) -> int:
        manager = ProjectManager()
        manager.delete_project(
            Project(identifier=self.args.project_identifier)
        )
        LOG.i("Deleted project '%s'.", self.args.project_identifier)
        return 0
