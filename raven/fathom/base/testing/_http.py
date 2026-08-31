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
"""Implementation of the `ConnectionHTTP` interface providing
a mock for testing.
"""

from typing import Optional

from raven.fathom.base.http import (
    ConnectionHTTP,
    RequestHTTP,
    ResponseHTTP,
    ConnectionException,
)


class ConnectionHTTPMock(ConnectionHTTP):
    """Mock implementation of `ConnectionHTTP` that does not perform
    real network I/O.

    Each call to `send()` returns the next pre-configured `ResponseHTTP`
    from the `responses` queue. If `responses` is exhausted, the fixed
    `default_response` is returned instead.

    When `raise_on_send` is set to a `ConnectionException`, that exception
    is raised on the next call (only the next) to `send()`.

    All requests passed to `send()` are recorded in `sent_requests` so that
    tests can assert on what was sent.

    Attributes:
        default_response (ResponseHTTP): The response returned by `send()`
            when the `responses` queue is empty. Defaults to a 200 OK
            response with no body.
        responses (list[ResponseHTTP]): An ordered list of responses to
            return from consecutive calls to `send()`. Each response is
            consumed once returned.
        raise_on_send (ConnectionException): When set to a
            `ConnectionException` instance, the next call to `send()`
            raises it instead of returning a response. May be `None`.
        sent_requests (list[RequestHTTP]): All requests received by
            `send()`, in order.
    """

    def __init__(self):
        """Initializes a new `ConnectionHTTPMock` with default values."""
        self.default_response: ResponseHTTP = ResponseHTTP(
            status_code=200,
            headers=dict(),
            body_data=None,
        )
        self.responses: list[ResponseHTTP] = []
        self.raise_on_send: Optional[ConnectionException] = None
        self.sent_requests: list[RequestHTTP] = []

    def send(self, request):
        self.sent_requests.append(request)

        if self.raise_on_send is not None:
            ex = self.raise_on_send
            self.raise_on_send = None
            # Suppress false positive
            # pylint: disable=raising-bad-type
            raise ex

        if self.responses:
            return self.responses.pop(0)

        return self.default_response
