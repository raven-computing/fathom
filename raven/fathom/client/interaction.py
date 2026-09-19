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
"""Client-specific implementations for client-server-interactions."""

from raven.fathom.base import ServerInteraction
from raven.fathom.base import TransmissionException
from raven.fathom.base import RequestParcelJSON, ResponseParcelJSON
from raven.fathom.base import ParcelEncodingException, ParcelDecodingException
from raven.fathom.base import HTTPEncodeException
from raven.fathom.base import MethodHTTP
from raven.fathom.base import ConnectionException
from raven.fathom.client.http import RequestHTTP
from raven.fathom.client.locator import ServerLocator, server_locator_to_url
from raven.fathom.client.logging import Logger


LOG = Logger.get()


class ServerInteractionHTTP(ServerInteraction):
    """Client implementation of the `ServerInteraction` interface.

    This implementation uses HTTP-based network connections
    to communicate with a server.
    """

    def __init__(self, location: ServerLocator):
        """Initializes a new `ServerInteractionHTTP` instance.

        Args:
            location (ServerLocator): The location of the server to connect to.
        """
        super().__init__()
        url = server_locator_to_url(location)
        url.path += "/interact/call"
        self._server_url = url

    def process(self, request):
        LOG.d("Processing client request:")
        LOG.d("%r", request)
        try:
            return self._send_http(request)
        except HTTPEncodeException as ex:
            raise TransmissionException(
                "Failed to encode client HTTP request"
            ) from ex
        except ParcelEncodingException as ex:
            raise TransmissionException(
                "Failed to encode client JSON request payload"
            ) from ex
        except ConnectionException as ex:
            raise TransmissionException(
                f"Could not connect to server at '{self._server_url}'"
            ) from ex
        except ParcelDecodingException as ex:
            raise TransmissionException(
                "Failed to decode JSON payload of server response"
            ) from ex

    def _send_http(self, request):
        http_request = RequestHTTP(MethodHTTP.POST, self._server_url)
        authentication = request.authentication
        if authentication is not None:
            http_request.set_authentication(authentication)

        parcel = RequestParcelJSON(request)
        http_request.set_body(parcel.encode())
        http_request.set_header("Content-Type", parcel.content_type())
        LOG.d("Sending HTTP request:")
        LOG.d("%r", http_request)

        http_response = http_request.send()

        LOG.d("Received HTTP response:")
        LOG.d("%r", http_response)
        if not http_response.ok:
            raise TransmissionException(
                "Server has responded "
                f"with HTTP status code {http_response.status_code}"
            )

        return ResponseParcelJSON(http_response.get_body()).decode()
