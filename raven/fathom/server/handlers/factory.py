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
"""Factories for server `ActionHandler` objects."""

from typing import Optional

from raven.fathom.base import ClientRequest, Interaction
from raven.fathom.base import SystemClock
from raven.fathom.server.config import ConfigurationManager
from raven.fathom.server.security import DeploymentAuthorizer, UserAuthorizer
from raven.fathom.server.deployment import DeploymentManager
from raven.fathom.server.user_management import UserManager
from raven.fathom.server.project_management import ProjectManager

from .handler import ActionHandler
from .server_info import ServerInfoHandler
from .deployment_intent import DeploymentIntentHandler
from .deployment_transaction import DeploymentTransactionHandler
from .user_management import (
    UserCreateHandler, UserListHandler, UserDeleteHandler,
)
from .project_management import (
    ProjectCreateHandler, ProjectListHandler, ProjectDeleteHandler,
)


class HandlerFactory:
    """Factory class for creating `ActionHandler` objects."""

    def create_action_handler_for(
        self,
        request: ClientRequest
    ) -> Optional[ActionHandler]:
        """Creates a new `ActionHandler` object capable of processing
        the specified client request.

        Args:
            request (ClientRequest): The client request to create
                an action handler for.

        Returns:
            ActionHandler: An `ActionHandler` implementation suitable
                for the specified request, or `None` if no suitable handler
                is available.
        """
        handler = None
        client_action = request.action
        if client_action == Interaction.QUERY_SERVER_INFO:
            handler = ServerInfoHandler()
        elif client_action == Interaction.REQUEST_DEPLOYMENT:
            handler = DeploymentIntentHandler(
                DeploymentAuthorizer(SystemClock())
            )
        elif client_action == Interaction.TRANSACT_DEPLOYMENT:
            handler = DeploymentTransactionHandler(
                DeploymentAuthorizer(SystemClock()),
                DeploymentManager(ConfigurationManager().get_server_config())
            )
        elif client_action == Interaction.CREATE_USER:
            handler = UserCreateHandler(UserAuthorizer(), UserManager())
        elif client_action == Interaction.LIST_USERS:
            handler = UserListHandler(UserAuthorizer(), UserManager())
        elif client_action == Interaction.DELETE_USER:
            handler = UserDeleteHandler(UserAuthorizer(), UserManager())
        elif client_action == Interaction.CREATE_PROJECT:
            handler = ProjectCreateHandler(UserAuthorizer(), ProjectManager())
        elif client_action == Interaction.LIST_PROJECTS:
            handler = ProjectListHandler(UserAuthorizer(), ProjectManager())
        elif client_action == Interaction.DELETE_PROJECT:
            handler = ProjectDeleteHandler(UserAuthorizer(), ProjectManager())

        return handler
