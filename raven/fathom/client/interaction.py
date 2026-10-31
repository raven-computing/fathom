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
from raven.fathom.base import ClientRequest, ServerResponse
from raven.fathom.base import TransmissionException, ProcessingException
from raven.fathom.base import RequestParcelJSON, ResponseParcelJSON
from raven.fathom.base import ParcelEncodingException, ParcelDecodingException
from raven.fathom.base import HTTPEncodeException
from raven.fathom.base import MethodHTTP
from raven.fathom.base import ConnectionException
from raven.fathom.base import ResponseHTTP
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

    def process(self, request: ClientRequest) -> ServerResponse:
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
                "Could not connect to server "
                f"at '{self._server_url.authority}'"
            ) from ex
        except ParcelDecodingException as ex:
            raise TransmissionException(
                "Failed to decode JSON payload of server response"
            ) from ex

    def _handle_failure_status(self, response: ResponseHTTP):
        if response.status.is_server_error():
            raise ProcessingException(
                "The server has failed to process the request and "
                f"has responded with HTTP status code {response.status}"
            )

        raise TransmissionException(
            "The connection to the server was established but the application "
            "server did not get to process the request. The server "
            f"has responded with HTTP status code {response.status}"
        )

    def _send_http(self, request: ClientRequest) -> ServerResponse:
        self._server_url.query["action"] = request.action
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
            self._handle_failure_status(http_response)

        return ResponseParcelJSON(http_response.get_body()).decode()
