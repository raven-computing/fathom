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
"""Implementation of `Provider` for the client package."""

from raven.fathom.base import TypeCheck
from raven.fathom.base import AbstractProvider, DirectImplementation
from raven.fathom.base import ServerInteraction
from raven.fathom.client.interaction import ServerInteractionHTTP
from raven.fathom.client.locator import ServerLocator


class ServerConnImpl(DirectImplementation):
    """Forwards the ServerLocator argument to
    the `ServerInteractionHTTP` initializer.
    """

    _ERR_HINT = (
        f"The concrete class {ServerInteractionHTTP} which implements "
        f"the requested interface {ServerInteraction} requires that "
        "the location of the server to connect to is specified as a "
        f"positional argument of type {ServerLocator}"
    )

    def forward_arguments(self, *args, **kwargs):
        if len(args) != 1:
            raise TypeError(ServerConnImpl._ERR_HINT)

        location = args[0]
        TypeCheck.require_arg(
            location, ServerLocator,
            message=(
                ServerConnImpl._ERR_HINT
                + f": Got {type(location)} instead"
            )
        )
        return (location,)


class ClientProvider(AbstractProvider):
    """Client-specific `Provider` implementation."""

    def initialize_bindings(self):
        self.bind(ServerInteraction, ServerConnImpl(ServerInteractionHTTP))
