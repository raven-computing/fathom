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
"""CLI command handling for the deploy command."""

from raven.fathom.client.config import ConfigurationManager
from raven.fathom.client.logging import Logger
from raven.fathom.client.documentation import DocumentationResource, DocsDir
from raven.fathom.client.connection import ServerConnectionException
from raven.fathom.client.filter_loader import load_filters
from raven.fathom.client.deployment import FathomDeployment
from raven.fathom.client.locator import load_server_locator
from raven.fathom.client.authentication import load_client_authentication
from raven.fathom.client.project import load_client_project
from raven.fathom.client.cli.command import Command
from raven.fathom.client.cli.status import ExitStatus


LOG = Logger.get()


class DeployCommand(Command):
    """Implementation of the 'deploy' CLI command."""

    def execute(self):
        try:
            return self._deploy()
        except ServerConnectionException as ex:
            LOG.e(str(ex))
            return ExitStatus.SERVER_UNREACHABLE

    def _deploy(self):
        LOG.i("Deploying project...")

        config = ConfigurationManager()
        project = load_client_project(config.get_project_config())
        if not project.identifier:
            LOG.e(
                "Project identifier is missing. "
                "Cannot proceed with deployment"
            )
            return ExitStatus.FAILURE

        if not project.assets:
            LOG.e(
                "Project assets are missing. "
                "Cannot proceed with deployment"
            )
            return ExitStatus.FAILURE

        docs = DocumentationResource()
        try:
            docs += DocsDir(project.assets)
        except ValueError:
            LOG.e(
                "Failed to load documentation resources "
                "from project assets directory:"
            )
            LOG.e("at: '%s'", project.assets)
            return ExitStatus.FAILURE

        for file_filter in load_filters(config.get_project_config()):
            docs.apply_filter(file_filter)

        location = load_server_locator(
            self.args,
            config.get_user_config(),
            config.get_project_config()
        )

        deployment = FathomDeployment(location)
        deployment.use_authentication(
            load_client_authentication(self.args, config.get_user_config())
        )
        deployment.set_project(project)
        deployment.add_resource(docs)

        deployment = deployment.deploy()

        if deployment.is_successful():
            LOG.i("Deployment SUCCESSFUL")
        else:
            LOG.i("Deployment FAILED")
            LOG.i(deployment.info_message or "")
            return ExitStatus.FAILURE

        return ExitStatus.SUCCESS
