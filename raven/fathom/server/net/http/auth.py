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
"""HTTP-related authentication utilities.

Provides the `decode_client_auth_header()` function to get client
authentication information from headers.
"""

import cherrypy

from raven.fathom.base import ClientAuthentication
from raven.fathom.base import HTTP_HEADER_CLIENT_AUTHENTICATION
from raven.fathom.base import ClientAuthenticationHeader


def decode_client_auth_header() -> ClientAuthentication:
    """Decodes the client authentication header from the currently
    serving HTTP request.

    Returns:
        ClientAuthentication: The authentication credentials submitted
            by a client in the underlying request header.

    Raises:
        HTTPError: If an HTTP error response should be submitted.
        HTTPDecodeException: If the submitted HTTP header is malformed.
    """
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

    return ClientAuthenticationHeader(auth_header).decode()
