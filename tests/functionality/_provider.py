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
"""Implementations of `Provider` to be used in functionality tests.

These providers override the `SystemEnvironment` binding so that the
client and server each receive their own `FunctionalityTestEnvironment`
subclass, allowing the test framework to control their home directories,
working directories, and environment variables independently.
"""

from raven.fathom.base.provider import Namespace
from raven.fathom.base.system import SystemEnvironment
from raven.fathom.client._provider import ClientProvider
from raven.fathom.server._provider import ServerProvider

from tests.functionality._env import ClientEnvironment, ServerEnvironment


class ClientFunctionalityTestProvider(ClientProvider):
    """A `Provider` to be used by client code in functionality tests."""

    def namespace(self):
        return Namespace("raven.fathom.client")

    def reusables(self): # type: ignore
        return [ClientEnvironment]

    def initialize_bindings(self):
        super().initialize_bindings()
        self.bind_override(SystemEnvironment, ClientEnvironment)


class ServerFunctionalityTestProvider(ServerProvider):
    """A `Provider` to be used by server code in functionality tests."""

    def namespace(self):
        return Namespace("raven.fathom.server")

    def reusables(self): # type: ignore
        return [ServerEnvironment]

    def initialize_bindings(self):
        super().initialize_bindings()
        self.bind_override(SystemEnvironment, ServerEnvironment)
