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
"""HTTP-server user sign-up controller."""

from raven.fathom.base import MethodHTTP, StatusHTTP
from raven.fathom.base import HTTPDecodeException
from raven.fathom.base import User, UserState
from raven.fathom.base import ClientAuthentication
from raven.fathom.base import ResponseStatusHTTP
from raven.fathom.server.core.logging import Logger
from raven.fathom.server.core.user_management import UserManager
from raven.fathom.server.core.user_management import UserInternalException
from raven.fathom.server.core.user_management import UserManagementException
from raven.fathom.server.security import UserAuthenticator
from raven.fathom.server.net.http.controller import Controller
from raven.fathom.server.net.http.decorators import expose
from raven.fathom.server.net.http.decorators import input_json, output_json
from raven.fathom.server.net.http.auth import decode_client_auth_header
from raven.fathom.server.net.http.status import ResponseObjectJSON


LOG = Logger.get()


def signup_user(
    authenticator: UserAuthenticator,
    authentication: ClientAuthentication,
    user: User
) -> tuple[ResponseStatusHTTP, ResponseObjectJSON]:
    """Performs a user sign-up, including the necessary
    request authentication.
    """
    auth = authenticator.authenticate_signup_request(authentication)
    if not auth.is_authenticated():
        return StatusHTTP.UNAUTHORIZED, {
            "status": "Failure",
            "message": "Authentication failed",
        }

    UserManager(authenticator).sign_up_user(user)

    LOG.i("User %s has signed up", user.identifier)
    return StatusHTTP.OK, {
        "status": "OK",
        "message": (
            f"User {user.identifier} "
            "has been successfully signed up."
        )
    }


class SignupController(Controller):
    """Controller for the user sign-up process."""

    @expose(MethodHTTP.POST)
    @input_json()
    @output_json()
    def signup(self) -> ResponseObjectJSON:
        """Handles a user sign-up."""
        authentication = ClientAuthentication()
        try:
            authentication = decode_client_auth_header()
            request_body = self.get_request_body_json()
            http_status, response_object = signup_user(
                UserAuthenticator(),
                authentication,
                User(
                    identifier=authentication.username,
                    password=request_body.get("set_password", ""),
                    state=UserState.ONBOARDING,
                )
            )
            self.set_response_status(http_status)
            return response_object
        except HTTPDecodeException as ex:
            LOG.e(ex)
            self.set_response_status(StatusHTTP.BAD_REQUEST)
            return {
                "status": "Error",
                "message": "The request is malformed.",
            }
        except UserInternalException as ex:
            LOG.e(
                "User %s requested a user sign-up"
                "but an internal error has occurred:",
                authentication.username,
            )
            LOG.e(ex)
            self.set_response_status(StatusHTTP.INTERNAL_SERVER_ERROR)
            return {
                "status": "Error",
                "message": "An internal error has occurred.",
            }
        except UserManagementException as ex:
            LOG.i(
                "User %s requested a user sign-up"
                "but the operation was rejected: %s",
                authentication.username,
                str(ex),
            )
            self.set_response_status(StatusHTTP.BAD_REQUEST)
            return {
                "status": "Failure",
                "message": str(ex),
            }
