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

from enum import StrEnum
from dataclasses import dataclass

from raven.fathom.base import ClientAuthentication
from raven.fathom.base import User
from raven.fathom.base import MethodHTTP
from raven.fathom.base import ConnectionException, HTTPEncodeException
from raven.fathom.base import JSONDecodeException
from raven.fathom.client.http import RequestHTTP
from raven.fathom.client.locator import ServerLocator, server_locator_to_url
from raven.fathom.client.exceptions import FathomClientException


class SignupConnectionException(FathomClientException):
    """An error has occurred while communicating with the server."""


class ResultStatus(StrEnum):
    """Enumeration of user sign-up response status."""

    OK = "OK"

    FAILURE = "Failure"

    ERROR = "Error"


@dataclass
class SignupResult:
    """Result type for user sign-up requests."""

    status: ResultStatus

    message: str


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

    def send(self) -> SignupResult:
        """Sends the user sign-up request to the Fathom server.

        This method blocks until the server responds.

        Returns:
            SignupResult: The result status of the sign-up request.

        Raises:
            SignupConnectionException: If a connection to the server cannot
                be established or the request encounters an unexpected error.
        """
        server_url = server_locator_to_url(self._location)
        server_url.path += "/user/signup"
        http_request = RequestHTTP(MethodHTTP.POST, server_url)
        try:
            return self._send(http_request)
        except (HTTPEncodeException, ConnectionException) as ex:
            raise SignupConnectionException(
                "An error occurred while trying to send user sign-up request"
            ) from ex
        except JSONDecodeException as ex:
            raise SignupConnectionException(
                "An error occurred while trying to decode the server response "
                "of a sent user sign-up request"
            ) from ex

    def _send(self, http_request: RequestHTTP) -> SignupResult:
        authentication = self._auth
        if authentication is not None:
            http_request.set_authentication(authentication)

        http_request.set_json_body({
            "set_password": self._user.password,
        })
        http_response = http_request.send()
        return self._get_response_from(http_response.get_body_json())

    def _get_response_from(self, response_obj: dict) -> SignupResult:
        status_string = response_obj.get("status")
        if status_string is None:
            raise SignupConnectionException(
                "Received unexpected status is response: "
                "Server did not specify result status"
            )

        status = self._get_result_status_from(status_string)
        return SignupResult(
            status=status,
            message=response_obj.get("message", "")
        )

    def _get_result_status_from(self, status: str) -> ResultStatus:
        try:
            return ResultStatus(status)
        except (ValueError, TypeError):
            raise SignupConnectionException(
                f"Received unexpected status '{status}'"
            )
