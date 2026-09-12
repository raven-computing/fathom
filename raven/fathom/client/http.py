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
"""Extensions to the base HTTP classes used by the Fathom client."""

from raven.fathom.base import RequestHTTP as BaseRequestHTTP
from raven.fathom.base import MethodHTTP
from raven.fathom.base import URL
from raven.fathom.base import ClientAuthentication
from raven.fathom.base import HTTP_HEADER_CLIENT_AUTHENTICATION
from raven.fathom.base import ClientAuthenticationHeader
from raven.fathom.client.version import Version


class RequestHTTP(BaseRequestHTTP):
    """Extension to the base `RequestHTTP` class.

    This HTTP client should be used by the Fathom client.
    """

    def __init__(self, method: MethodHTTP, url: URL):
        super().__init__(method, url)
        self.set_header("User-Agent", f"Fathom-client/{Version.current()}")

    def set_authentication(self, authentication: ClientAuthentication):
        """Applies the specified Fathom-specific authentication credentials.

        Args:
            authentication (ClientAuthentication): The authentication details
                of the Fathom client.

        Raises:
            HTTPEncodeException: If the specified authentication cannot
                be encoded for this HTTP request.
        """
        self.set_header(
            HTTP_HEADER_CLIENT_AUTHENTICATION,
            ClientAuthenticationHeader(authentication).encode()
        )
