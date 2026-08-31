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

from raven.fathom.base import ServerConnection
from raven.fathom.base import URL, URLAuthority
from raven.fathom.base import TransmissionException
from raven.fathom.base import RequestParcelJSON, ResponseParcelJSON
from raven.fathom.base import ParcelEncodingException, ParcelDecodingException
from raven.fathom.base import ClientAuthenticationHeader
from raven.fathom.base import HTTPEncodeException
from raven.fathom.base import RequestHTTP, MethodHTTP
from raven.fathom.base import ConnectionException
from raven.fathom.base import HTTP_HEADER_CLIENT_AUTHENTICATION
from raven.fathom.client.locator import ServerLocator
from raven.fathom.client.version import Version


class ServerConnectionHTTP(ServerConnection):
    """Client implementation of the `ServerConnection` interface.

    This implementation uses HTTP-based network connections
    to communicate with a server.
    """

    def __init__(self, location: ServerLocator):
        """Initializes a new `ServerConnectionHTTP` instance.

        Args:
            location (ServerLocator): The location of the server to connect to.
        """
        super().__init__()
        url = URL()
        url.scheme = "https" if location.secure_connection else "http"
        url.authority = URLAuthority(
            hostname=location.domain,
            port=location.port
        )
        if location.location is not None:
            url.path = location.location

        url.path += "/fathom/v1/interact/call"
        self._server_url = url

    def process(self, request):
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
        http_request.set_header(
            "User-Agent",
            f"Fathom-client/{Version.current()}"
        )
        authentication = request.authentication
        if authentication is not None:
            http_request.set_header(
                HTTP_HEADER_CLIENT_AUTHENTICATION,
                ClientAuthenticationHeader(authentication).encode()
            )

        parcel = RequestParcelJSON(request)
        http_request.set_body(parcel.encode())
        http_request.set_header("Content-Type", parcel.content_type())
        http_response = http_request.send()
        return ResponseParcelJSON(http_response.get_body()).decode()
