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
"""The Fathom HTTP-server.

Implements the HTTP-specific server facilities.
It contains a `ServerHTTP` class to create and start a standalone fully-capable
HTTP-server which runs a Fathom `ServerApplication` instance to serve the
endpoints provided by the Fathom server component.
"""

import platform
import errno
import socket

from typing import Optional
from multiprocessing.synchronize import Event

import cherrypy

from raven.fathom.base import SystemEnvironment, OperatingSystem
from raven.fathom.base import Configuration
from raven.fathom.base import ApplicationContext, ApplicationMode
from raven.fathom.server.config import ServerConfiguration
from raven.fathom.server.logging import ServerLogger
from raven.fathom.server.exceptions import FathomServerException


LOG = ServerLogger.get()

_SERVER_HTTP = None


class HTTPServerStartException(FathomServerException):
    """Exception raised when the HTTP server fails to start."""


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


class ServerHTTP:
    """The Fathom HTTP server using CherryPy."""

    def __init__(
        self,
        app: ServerApplication,
        config: Optional[Configuration] = None,
        event: Optional[Event] = None
    ):
        """Initializes a new `ServerHTTP` instance.

        Args:
            app (ServerApplication): The server application instance to serve.
            config (Configuration): The server configuration to use. An empty
                configuration will be used if none is provided.
            event (Event): An optional `multiprocessing.synchronize.Event` that
                the server will use to signal when it is ready to
                accept requests.
        """
        config = config or Configuration()
        section = config.get_section(ServerConfiguration.SERVER)
        self._app = app
        self._config = config
        self._address = section[ServerConfiguration.SERVER.ADDRESS_LISTEN]
        self._port = section[ServerConfiguration.SERVER.PORT_LISTEN]
        self._event_ready = event

    def get_application(self) -> ServerApplication:
        """Gets the server application instance being served.

        Returns:
            ServerApplication: The server application instance.
        """
        return self._app

    def start(self):
        """Starts the server.

        Raises:
            HTTPServerStartException: If the server fails to start.
        """
        app_mode = ApplicationContext.instance().get_application_mode()
        in_dev_mode = app_mode == ApplicationMode.DEVELOPMENT

        thread_pool_size = self._config_of(
            ServerConfiguration.SERVER.THREAD_POOL_SIZE
        )
        gzip_compression_enabled = self._config_of(
            ServerConfiguration.SERVER.ENABLE_GZIP_COMPRESSION
        )
        max_header_size = self._config_of(
            ServerConfiguration.SERVER.MAX_REQUEST_HEADER_SIZE
        )
        max_body_size = self._config_of(
            ServerConfiguration.SERVER.MAX_REQUEST_BODY_SIZE
        )

        # Global configuration
        cherrypy.config.update({
            "server.socket_host": self._address,
            "server.socket_port": self._port,
            "server.thread_pool": thread_pool_size,
            "server.max_request_header_size": max_header_size.in_bytes(),
            "server.max_request_body_size": max_body_size.in_bytes(),
            "tools.proxy.on": False,
            "tools.sessions.on": False,
            "tools.gzip.on": gzip_compression_enabled,
            "tools.log_headers.on": in_dev_mode,
            "engine.autoreload.on": in_dev_mode,
            "request.show_tracebacks": in_dev_mode,
            "request.show_mismatched_params": in_dev_mode,
            "checker.on": in_dev_mode,
        })

        # Application configuration
        config = {
            "/": {
                "error_page.default": self._app.on_request_error,
                "request.error_response": self._app.on_unhandled_error,
            }
        }

        LOG.log(f"Running on Python {platform.python_version()}")
        cherrypy.config.update(config)
        app_root_path = self._app.root_path()
        LOG.log(f"Mounting application endpoints to path '{app_root_path}'")
        cherrypy.request.hooks.attach(
            "before_finalize",
            self._app.on_request_processed
        )
        cherrypy.tree.mount(self._app, app_root_path, config)
        cherrypy.engine.subscribe("before_request", self._app.on_request_start)
        cherrypy.engine.subscribe("after_request", self._app.on_request_end)
        cherrypy.engine.signals.subscribe() # type: ignore
        LOG.log("Starting HTTP engine")
        self._start_engine()
        LOG.log("HTTP engine started")

    def run(self):
        """Runs the server loop.

        The server must first be started.
        This is a blocking call.
        """
        LOG.log("Fathom HTTP server ready to accept requests")
        if self._event_ready is not None:
            self._event_ready.set()

        cherrypy.engine.block()
        LOG.log("Stopping")

    def status_code(self) -> int:
        """Returns the status code of the server.

        Returns:
            int: The status code of the HTTP server.
        """
        return 0

    @staticmethod
    def get_assigned_server() -> "ServerHTTP":
        """Gets the server instance that was assigned to this application.

        Returns:
            ServerHTTP: The assigned server instance.
        
        raises:
            RuntimeError: If no server instance has been assigned.
        """
        if _SERVER_HTTP is None:
            raise RuntimeError("No server instance has been assigned yet")

        return _SERVER_HTTP

    def _config_of(self, key):
        return self._config.get_required_value(
            key,
            or_raise=HTTPServerStartException
        )

    def _start_engine(self):
        try:
            if self._config[ServerConfiguration.SERVER.PORT_CHECK_BIND]:
                self._try_bind_socket()

            cherrypy.engine.start()
        except OSError as error:
            LOG.log("Error: Failed to start HTTP engine")
            if error.strerror:
                LOG.log(error.strerror)

            msg = str(error)
            if error.errno == errno.EACCES:
                msg = f"Insufficient permissions to bind to port {self._port}"
                LOG.log(msg)
            elif error.errno == errno.EADDRINUSE:
                msg = f"Port {self._port} is already in use by another process"
                LOG.log(msg)

            raise HTTPServerStartException(
                f"Failed to start HTTP engine: {msg}"
            ) from error

    def _try_bind_socket(self):
        """Explicitly checks if we can bind to the port before starting
        the engine because CherryPy binds to the socket in a separate thread
        and we can't cleanly handle that if an error occurs.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        os = SystemEnvironment.instance().get_operating_system()
        if os == OperatingSystem.GNU_LINUX:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if os == OperatingSystem.MS_WINDOWS:
            # pylint: disable=no-member
            sock.setsockopt(
                socket.SOL_SOCKET,
                socket.SO_EXCLUSIVEADDRUSE, # type: ignore
                1
            )

        try:
            sock.bind((self._address, self._port))
        finally:
            sock.close()


def assign(server: ServerHTTP) -> ServerHTTP:
    """Assigns the given server instance as the server being used for this app.

    Args:
        server (ServerHTTP): The server instance to assign.

    Returns:
        ServerHTTP: The server instance that was assigned.
    """
    # pylint: disable=W0603
    global _SERVER_HTTP
    _SERVER_HTTP = server
    return server
