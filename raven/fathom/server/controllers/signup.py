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

import cherrypy

from raven.fathom.base import MethodHTTP
from raven.fathom.base import HTTPDecodeException
from raven.fathom.base import User, UserState
from raven.fathom.server.logging import Logger
from raven.fathom.server.http_tools import expose, input_json, output_json
from raven.fathom.server.http_tools import decode_client_auth_header
from raven.fathom.server.security import UserAuthenticator
from raven.fathom.server.user_management import UserManager


LOG = Logger.get()


class SignupController:
    """Controller for the user sign-up process."""

    @expose(MethodHTTP.POST)
    @input_json()
    @output_json()
    def signup(self):
        """Controller method to handle user sign-up."""
        try:
            client_authentication = decode_client_auth_header()
            user = UserAuthenticator().authenticate_signup_request(
                client_authentication
            )
            if not user.is_authenticated():
                cherrypy.response.status = 401
                return {
                    "status": "Failure",
                    "message": "Authentication failed",
                }

            request_body = cherrypy.request.json
            user = User(
                identifier=client_authentication.username,
                password=request_body.get("set_password"),
                state=UserState.ONBOARDING,
            )
            UserManager().sign_up_user(user)
        except ValueError as error:
            LOG.e(error)
            cherrypy.response.status = 500
            return {
                "status": "Failure",
                "message": "An error has occurred.",
            }
        except HTTPDecodeException as ex:
            LOG.e(ex)
            cherrypy.response.status = 500
            return {
                "status": "Failure",
                "message": "An error has occurred.",
            }

        LOG.i("User '%s' has been signed up", user.identifier)
        return {
            "status": "OK",
            "message": "User signed up successfully."
        }
