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
from raven.fathom.base import TableFormatter
from raven.fathom.server.cli.command import ServerCommand
from raven.fathom.server.cli.status import ExitStatus
from raven.fathom.server.core.logging import Logger
from raven.fathom.server.domain.project import ProjectManager


LOG = Logger.get()


class ProjectCreateCommand(ServerCommand):
    """Implementation of `project create`."""

    def execute(self) -> int:
        project = Project(
            identifier=self.args.project_identifier,
            name=self.args.project_name,
            description=self.args.project_description,
        )
        LOG.d("Creating project '%s'", project.identifier)
        ProjectManager().create_project(project)
        LOG.i("Created project %s.", project.identifier)
        return ExitStatus.SUCCESS


class ProjectListCommand(ServerCommand):
    """Implementation of `project list`."""

    def execute(self) -> int:
        formatter = TableFormatter().set_headers(
            "Identifier", "Name", "Description"
        )
        LOG.d("Fetching project list")
        projects = ProjectManager().list_projects()
        for project in projects:
            formatter.add_row(
                project.identifier,
                project.name,
                project.description,
            )

        LOG.i("Project list:")
        self._print_table(formatter)
        return ExitStatus.SUCCESS


class ProjectDeleteCommand(ServerCommand):
    """Implementation of `project delete`."""

    def execute(self) -> int:
        project = Project(identifier=self.args.project_identifier)
        LOG.d("Deleting project '%s'", project.identifier)
        ProjectManager().delete_project(project)
        LOG.i("Deleted project '%s'.", self.args.project_identifier)
        return ExitStatus.SUCCESS
