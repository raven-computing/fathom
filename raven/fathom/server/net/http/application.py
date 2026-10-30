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
"""An HTTP-based web application.

Contains the `ServerApplication` class whose instance can be served
by an `ServerHTTP`.
"""

import cherrypy

from raven.fathom.server.core.logging import ServerLogger


LOG = ServerLogger.get()


class ServerApplication:
    """A server application.

    Concrete applications should subclass this class and override
    the desired methods.
    Routes must be defined in the subclass as public member instances
    of controllers.
    """

    def root_path(self) -> str:
        """Gets the root path of the application.

        Returns:
            str: The root path, with a leading '/'.
        """
        return "/"

    def on_request_start(self):
        """Handles the start of a request.

        This method is called right before a client request
        is processed by the HTTP server.
        """

    def on_request_processed(self):
        """Callback fired after a request is processed.

        This method is called right after a client request
        has been processed by the web controller but before the response
        is sent to the client.
        """
        # Remove version specifier from "Server" header
        cherrypy.serving.response.headers["Server"] = "CherryPy"

    def on_request_end(self):
        """Handles the end of a request.

        This method is called right after a client request
        has been processed by the HTTP server.
        """

    def on_request_error(
        self,
        status: str,
        message: str,
        *args,
        **kwargs
    ) -> str:
        """Handles a known error that occurred during request processing.

        A known error would be, for example, a 404 error (page not found).
        Must return a string or iterable of strings which will be set to
        `response.body`. It may also override headers or perform any
        other processing.
        """
        cherrypy.response.headers["Content-Type"] = "text/plain;charset=utf-8"
        return f"{status}\n\n{message}"

    def on_unhandled_error(self):
        """Handles an unanticipated error that occurred during
        request processing.
        """
        cherrypy.response.status = 500
        try:
            cherrypy.response.body = "Internal server error".encode("UTF-8")
        except UnicodeEncodeError:
            LOG.log(
                "Error: Failed to encode general error response body message"
            )

        cherrypy.response.headers["Content-Type"] = "text/plain;charset=utf-8"
