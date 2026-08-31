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
"""Implementation of `Provider` for the server package."""

from raven.fathom.base import AbstractProvider, DirectImplementation
from raven.fathom.base import ServerConnection
from raven.fathom.server.interaction import ServerConnectionImpl
from raven.fathom.server.dao import DataAccess
from raven.fathom.server.datastore._data_access import DataAccessRDBMS
from raven.fathom.server.security import UserAuthenticator
from raven.fathom.server.handlers import HandlerFactory


class ServerConnectionBinding(DirectImplementation):
    """Injects dependencies into the `ServerConnectionImpl` initializer."""

    def forward_arguments(self, *args, **kwargs):
        return UserAuthenticator(), HandlerFactory()


class ServerProvider(AbstractProvider):
    """Server-specific `Provider` implementation."""

    def initialize_bindings(self):
        self.bind_export(
            ServerConnection, ServerConnectionBinding(ServerConnectionImpl)
        )
        self.bind_export(DataAccess, DataAccessRDBMS)
