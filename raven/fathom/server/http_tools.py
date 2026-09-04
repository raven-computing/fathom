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
"""HTTP-controller-specific utilities.

Provides the `@fathom_client_request` and `@fathom_server_response` decorators
which handle the serialization and deserialization of HTTP-based client
requests and server responses. Therefore, when applying these decorators on
a controller method provides that method with an already
ready-to-use `ClientRequest` object as an argument. In return, the controller
method should return a `ServerResponse` object, which then gets automatically
serialized into the used HTTP format.
Validation is performed by the decorators.
"""

from functools import wraps
from typing import Union, Final

import cherrypy

from raven.fathom.base import MethodHTTP
from raven.fathom.base import ServerResponse
from raven.fathom.base import RequestParcelJSON, ResponseParcelJSON
from raven.fathom.base import ParcelEncodingException, ParcelDecodingException
from raven.fathom.base.http import HTTP_HEADER_CLIENT_AUTHENTICATION
from raven.fathom.base.http import ClientAuthenticationHeader
from raven.fathom.base.http import HTTPDecodeException
from raven.fathom.server.logging import Logger
from raven.fathom.server.datastore import DatabaseManager
from raven.fathom.server.parcel import ParcelValidatorJSON
from raven.fathom.server.parcel import ParcelValidationException
from raven.fathom.server.schemas import SchemaLoaderJSON


LOG = Logger.get()

_INTERACTION_CONTENT_TYPE: Final[str] = "application/json"


def expose(methods: Union[MethodHTTP, list[MethodHTTP]]):
    """Decorator to expose a controller method as an HTTP endpoint.

    The decorated controller method will be wrapped in a database context
    (open connection and new transaction) and will be exposed as
    an HTTP endpoint with the specified allowed methods.

    Args:
        methods: The HTTP method(s) to allow for the endpoint.
            Either as a single `MethodHTTP` or a `list` of `MethodHTTP`.
    """
    def decorator(controller_method):
        @cherrypy.tools.allow(methods=methods) # type: ignore
        @wraps(controller_method)
        def wrapper(*args, **kwargs):
            try:
                with DatabaseManager().get_database():
                    return controller_method(*args, **kwargs)
            except Exception as ex:
                LOG.e("Error occurred while processing request")
                LOG.e(ex, exc_info=ex)
                raise

        return cherrypy.expose(wrapper)
    return decorator


class _RequestProcessorHTTP(cherrypy.Tool):
    """CherryPy Tool to deserialize a HTTP client request
    into a `ClientRequest` object.
    """

    def __init__(self):
        super().__init__(
            "before_handler",
            self._process,
            name="fathom_request",
            priority=30
        )

    def _process(self):
        request = cherrypy.serving.request
        auth_header = request.headers.get(HTTP_HEADER_CLIENT_AUTHENTICATION)
        if not auth_header:
            raise cherrypy.HTTPError(
                401, "Unauthenticated request"
            )

        redacted_auth_val = "*****REDACTED*****"
        request.headers[HTTP_HEADER_CLIENT_AUTHENTICATION] = redacted_auth_val
        auth_header_lower = HTTP_HEADER_CLIENT_AUTHENTICATION.lower()
        for i, item in enumerate(request.header_list):
            name, _ = item
            if name.lower() == auth_header_lower:
                request.header_list[i] = (name, redacted_auth_val)
                break

        content_type = request.headers.get("Content-Type", "")
        if content_type != _INTERACTION_CONTENT_TYPE:
            raise cherrypy.HTTPError(
                415, "Expected an entity of content type application/json"
            )

        body = request.body
        if body is None:
            raise cherrypy.HTTPError(
                400,
                "Bad request: No request body specified"
            )

        data = body.read()
        try:
            client_request = RequestParcelJSON(
                data,
                ParcelValidatorJSON(SchemaLoaderJSON.for_request_schema())
            ).decode()
            client_request.authentication = ClientAuthenticationHeader(
                auth_header
            ).decode()
        except ParcelDecodingException:
            raise cherrypy.HTTPError(
                400, "Bad request: Expected a valid JSON entity"
            )
        except ParcelValidationException:
            raise cherrypy.HTTPError(
                400,
                "Bad request: Content validation failed. "
                "The request body does not represent a valid client request"
            )
        except HTTPDecodeException:
            raise cherrypy.HTTPError(
                400,
                "Bad request: Decode error"
            )

        request.params["request"] = client_request


def _fathom_handler(*args, **kwargs):
    request = cherrypy.serving.request
    assert hasattr(request, "fathom_inner_handler")
    server_response = request.fathom_inner_handler( # type: ignore
        *args, **kwargs
    )
    if not isinstance(server_response, ServerResponse):
        LOG.e(
            "A controller method has returned a value of an invalid type "
            "in a Fathom interaction. "
            "Return value must be a ServerResponse object"
            "This is a programming error."
        )
        raise cherrypy.HTTPError(500, "Internal server error.")

    try:
        response_parcel = ResponseParcelJSON(
            server_response,
            ParcelValidatorJSON(SchemaLoaderJSON.for_response_schema())
        ).encode()
    except ParcelEncodingException as ex:
        LOG.e("An error occurred while encoding server response:")
        LOG.e(ex)
        raise cherrypy.HTTPError(500, "Internal server error.")
    except ParcelValidationException as ex:
        LOG.e("An error occurred while validating server response:")
        LOG.e(ex)
        raise cherrypy.HTTPError(500, "Internal server error.")

    return response_parcel


class _ResponseProcessorHTTP(cherrypy.Tool):
    """CherryPy Tool to serialize a `ServerResponse` object
    to a HTTP server response.
    """

    def __init__(self):
        super().__init__(
            "before_handler",
            self._process,
            name="fathom_response",
            priority=31
        )

    def _process(self):
        request = cherrypy.serving.request
        response = cherrypy.serving.response
        # request.handler may be set to None by e.g. the caching tool
        # to signal to all components that a response body has already
        # been attached, in which case we don't need to wrap anything.
        if request.handler is None:
            return

        request.fathom_inner_handler = request.handler # type: ignore
        request.handler = _fathom_handler # type: ignore

        response.headers["Content-Type"] = _INTERACTION_CONTENT_TYPE


# Register tools with CherryPy
cherrypy.tools.fathom_request = _RequestProcessorHTTP()
cherrypy.tools.fathom_response = _ResponseProcessorHTTP()

# Expose tools
fathom_client_request = cherrypy.tools.fathom_request # type: ignore
fathom_server_response = cherrypy.tools.fathom_response # type: ignore
output_json = cherrypy.tools.json_out # type: ignore
