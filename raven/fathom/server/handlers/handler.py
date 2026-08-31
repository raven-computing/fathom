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
"""Declares an abstract base class for server action handlers."""

from abc import ABC, abstractmethod

from raven.fathom.base import ClientRequest, ServerResponse


class ActionHandler(ABC):
    """A server action handler.

    Handles a concrete client-server-interaction and produces
    the corresponding server response.
    """

    @abstractmethod
    def handle(self, request: ClientRequest, response: ServerResponse):
        """Handles the client-server-interaction.

        Args:
            request (ClientRequest): The client request of the interaction.
            response (ServerResponse): The server response of the interaction.

        Raises:
            Exception: If an error occurs while handling the interaction that
                could not be handled by the server by creating an appropriate
                response.
        """
