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
"""An HTTP-client implementation using urllib."""

import urllib.request
import urllib.error

from raven.fathom.base.http import ConnectionHTTP, RequestHTTP, ResponseHTTP
from raven.fathom.base.http import ConnectionException


class ConnectionHTTPImpl(ConnectionHTTP):
    """Implementation of `ConnectionHTTP` using urllib."""

    def send(self, request):
        try:
            return self._send(request)
        except urllib.error.HTTPError as error:
            return self._create_response_obj_from(error)
        except urllib.error.URLError as error:
            raise ConnectionException(str(error.reason)) from error
        except OSError as error:
            raise ConnectionException(str(error)) from error
        except UnicodeEncodeError as error:
            raise ConnectionException(
                f"Failed to encode request body: {error}"
            ) from error
        except Exception as ex:
            raise ConnectionException(
                f"Unexpected error encountered: {ex.__class__.__name__}"
            ) from ex

    def _send(self, request: RequestHTTP) -> ResponseHTTP:
        body = request.get_body()
        if body is not None and isinstance(body, str):
            body = body.encode("UTF-8")

        req = urllib.request.Request(
            url=str(request.url),
            data=body,
            headers=request.get_headers() or dict(),
            method=request.method,
        )
        timeout_seconds = request.timeout / 1_000
        with urllib.request.urlopen(req, timeout=timeout_seconds) as response:
            return self._create_response_obj_from(response)

    def _create_response_obj_from(self, urllib_resp):
        response = ResponseHTTP(
            urllib_resp.code,
            dict(urllib_resp.headers),
            urllib_resp.read()
        )
        urllib_resp.close()
        return response
