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
"""HTTP-server client-server-interaction web controller."""

from raven.fathom.base import MethodHTTP, StatusHTTP
from raven.fathom.base import ServerInteraction
from raven.fathom.base import ProcessingException
from raven.fathom.base import ClientRequest, ServerResponse
from raven.fathom.server.net.http_status import ResponseHTTP
from raven.fathom.server.net.http_tools import fathom_client_request
from raven.fathom.server.net.http_tools import fathom_server_response
from raven.fathom.server.net.http_tools import expose


class InteractionController:
    """Web controller for the Fathom interaction endpoint."""

    @expose(MethodHTTP.POST)
    @fathom_client_request()
    @fathom_server_response()
    def call(self, request: ClientRequest) -> ResponseHTTP[ServerResponse]:
        """Controller method to handle a client interaction."""
        try:
            return ServerInteraction.instance().process(request)
        except ProcessingException:
            return StatusHTTP.INTERNAL_SERVER_ERROR
