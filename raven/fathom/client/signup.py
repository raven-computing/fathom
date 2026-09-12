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
"""Provides a utility to connect to a Fathom server and sign up a new user."""

from raven.fathom.base import ClientAuthentication
from raven.fathom.base import User
from raven.fathom.base import URL, URLAuthority
from raven.fathom.base import ClientAuthenticationHeader
from raven.fathom.base import RequestHTTP, MethodHTTP
from raven.fathom.base import HTTP_HEADER_CLIENT_AUTHENTICATION
from raven.fathom.client.locator import ServerLocator
from raven.fathom.client.version import Version


class UserSignupRequest:
    """A request to sign up a new user on a Fathom server.

    Initialize a new instance and then call `send()` to send
    the request to a Fathom server.
    """

    def __init__(
        self,
        location: ServerLocator,
        authentication: ClientAuthentication,
        new_user: User
    ):
        """Initializes a new user sign-up request.

        Args:
            location (ServerLocator): The server to send the request to.
            authentication (ClientAuthentication): The client authentication
                used for the sign-up.
            new_user (User): The new user to sign up. Should contain the
                user's new password to set.
        """
        self._location = location
        self._auth = authentication
        self._user = new_user

    def send(self) -> str:
        """Sends the user sign-up request to the Fathom server.

        This method blocks until the server responds.

        Returns:
            str: The status of the sign-up request.

        Raises:
            ConnectionException: If there is an error connecting to the server.
            HTTPEncodeException: If there is an error encoding the
                HTTP request.
        """
        url = URL()
        url.scheme = "https" if self._location.secure_connection else "http"
        url.authority = URLAuthority(
            hostname=self._location.domain,
            port=self._location.port
        )
        if self._location.location is not None:
            url.path = self._location.location

        url.path += "/fathom/v1/user/signup"
        server_url = url
        http_request = RequestHTTP(MethodHTTP.POST, server_url)
        http_request.set_header(
            "User-Agent",
            f"Fathom-client/{Version.current()}"
        )
        authentication = self._auth
        if authentication is not None:
            http_request.set_header(
                HTTP_HEADER_CLIENT_AUTHENTICATION,
                ClientAuthenticationHeader(authentication).encode()
            )

        http_request.set_json_body({
            "identifier": self._user.identifier,
            "password": self._user.password,
        })
        http_response = http_request.send()
        response_body = http_response.get_body_json()
        return response_body.get("status", "FAILURE")
