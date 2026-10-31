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
"""A simple minimal zero-dependency HTTP-client.

Uses the builtin urllib standard library (implementation detail).

Also contains definitions related to HTTP-based communication between
Fathom clients and servers.

#### Enumerations:

* `MethodHTTP`
* `ResponseClassHTTP`
* `StatusHTTP`

#### Classes:

* `RequestHTTP`
* `ResponseHTTP`
* `StatusCodeHTTP`
* `StatusCodeRangeHTTP`
* `ResponseStatusHTTP`
* `ConnectionHTTP`
* `ClientAuthenticationHeader`

#### Constants:

* `HTTP_HEADER_CLIENT_AUTHENTICATION`

#### Exceptions:

The following diagram illustrates the exception hierarchy:

```

HttpException
      |
      |-- ConnectionException
      |
      |-- HTTPEncodeException
      |
      |-- HTTPDecodeException

```

Author: Phil Gaiser
"""

import base64
import binascii
import json

from abc import abstractmethod
from enum import Enum, StrEnum
from dataclasses import dataclass
from typing import Optional, Final, Union, Annotated

from raven.fathom.base.typing import Interface, TypeCheck
from raven.fathom.base.url import URL
from raven.fathom.base.decorators import inject
from raven.fathom.base.authentication import ClientAuthentication
from raven.fathom.base.exceptions import FathomBaseException


# The HTTP header name used by clients for authentication to the server.
HTTP_HEADER_CLIENT_AUTHENTICATION = "Fathom-Authentication"


class HttpException(FathomBaseException):
    """Base exception for HTTP-related errors."""


class ConnectionException(HttpException):
    """Signals a failed connection attempt."""


class HTTPEncodeException(HttpException):
    """An encoding error has occurred for some HTTP-related part."""


class HTTPDecodeException(HttpException):
    """A decoding error has occurred for some HTTP-related part."""


StatusCodeHTTP = Annotated[int, "must be in range [100, 599]"]


def _is_valid_http_status_code(code: StatusCodeHTTP) -> bool:
    return 100 <= code <= 599


@dataclass(frozen=True)
class StatusCodeRangeHTTP:
    """Represents a range of HTTP status codes.

    Attributes:
        minimum (StatusCodeHTTP): The lowest status code
            in the range (inclusive).
        maximum (StatusCodeHTTP): The highest status code
            in the range (inclusive).
    """

    minimum: StatusCodeHTTP

    maximum: StatusCodeHTTP

    def __post_init__(self):
        if not _is_valid_http_status_code(self.minimum):
            raise ValueError(
                f"Invalid HTTP status code for minimum {self.minimum}"
            )

        if not _is_valid_http_status_code(self.maximum):
            raise ValueError(
                f"Invalid HTTP status code for maximum {self.maximum}"
            )

        if self.minimum > self.maximum:
            raise ValueError(
                "Invalid HTTP status code range. "
                "Minimum must be less than or equal maximum"
            )


class ResponseClassHTTP(Enum):
    """Enumeration of standard HTTP response status code classes."""

    INFORMATIONAL = StatusCodeRangeHTTP(100, 199)

    SUCCESS = StatusCodeRangeHTTP(200, 299)

    REDIRECTION = StatusCodeRangeHTTP(300, 399)

    CLIENT_ERROR = StatusCodeRangeHTTP(400, 499)

    SERVER_ERROR = StatusCodeRangeHTTP(500, 599)


class ResponseStatusHTTP:
    """An HTTP response status that can be returned by a HTTP server.

    This class is immutable.

    Attributes:
        code (StatusCodeHTTP): The numeric HTTP status code.
        reason (str): The reason phrase.
    """

    __slots__ = ("_code", "_reason")

    def __init__(self, code: StatusCodeHTTP, reason: str):
        if not _is_valid_http_status_code(code):
            raise ValueError(
                "ResponseStatusHTTP.code must be in range [100, 599] but "
                f"got {code!r}"
            )

        self._code = code
        self._reason = reason

    @property
    def code(self) -> StatusCodeHTTP:
        """The numeric HTTP status code, as a `StatusCodeHTTP`."""
        return self._code

    @property
    def reason(self) -> str:
        """The HTTP reason phrase, as a `str`."""
        return self._reason

    def is_informational(self) -> bool:
        """Indicates whether the status code belongs in
        the **informational** responses class.

        Returns:
            bool:`True` if the numeric status code is in the range [100, 199],
                `False` otherwise.
        """
        return self._is_in_class_range(ResponseClassHTTP.INFORMATIONAL)

    def is_success(self) -> bool:
        """Indicates whether the status code belongs in
        the **success** responses class.

        Returns:
            bool:`True` if the numeric status code is in the range [200, 299],
                `False` otherwise.
        """
        return self._is_in_class_range(ResponseClassHTTP.SUCCESS)

    def is_redirection(self) -> bool:
        """Indicates whether the status code belongs in
        the **redirection** responses class.

        Returns:
            bool:`True` if the numeric status code is in the range [300, 399],
                `False` otherwise.
        """
        return self._is_in_class_range(ResponseClassHTTP.REDIRECTION)

    def is_client_error(self) -> bool:
        """Indicates whether the status code belongs in
        the **client error** responses class.

        Returns:
            bool:`True` if the numeric status code is in the range [400, 499],
                `False` otherwise.
        """
        return self._is_in_class_range(ResponseClassHTTP.CLIENT_ERROR)

    def is_server_error(self) -> bool:
        """Indicates whether the status code belongs in
        the **server error** responses class.

        Returns:
            bool:`True` if the numeric status code is in the range [500, 599],
                `False` otherwise.
        """
        return self._is_in_class_range(ResponseClassHTTP.SERVER_ERROR)

    def _is_in_class_range(self, response: ResponseClassHTTP) -> bool:
        return response.value.minimum <= self.code <= response.value.maximum

    def __eq__(self, other):
        if isinstance(other, int):
            return self.code == other

        if isinstance(other, Enum):
            value = getattr(other, "value", None)
            if isinstance(value, ResponseStatusHTTP):
                return self.code == value.code

        if isinstance(other, ResponseStatusHTTP):
            return self.code == other.code

        raise TypeError(
            "Cannot compare ResponseStatusHTTP instance "
            f"with object of type {type(other)}"
        )

    def __hash__(self):
        return hash(self.code)

    def __repr__(self):
        return (
            "ResponseStatusHTTP("
            f"code={self.code!r}, reason={self.reason!r})"
        )


class MethodHTTP(StrEnum):
    """Enumeration of HTTP methods."""

    OPTIONS = "OPTIONS"

    GET = "GET"

    HEAD = "HEAD"

    POST = "POST"

    PUT = "PUT"

    DELETE = "DELETE"

    TRACE = "TRACE"

    PATCH = "PATCH"


class ResponseHTTP:
    """The response to a sent HTTP request."""

    def __init__(
        self,
        status: ResponseStatusHTTP,
        headers: dict[str, str],
        body_data: Optional[bytes]
    ):
        """Initializes a new `ResponseHTTP` instance.

        Args:
            status (ResponseStatusHTTP): The response status sent
                by the server.
            headers (dict): The response HTTP headers.
            body_data (bytes): The raw response body data, as `bytes`.
                May be `None` if the server has not responded
                with any body data.
        """
        self._status = status
        self._headers = headers or dict()
        self._body = body_data

    @property
    def status(self) -> ResponseStatusHTTP:
        """The response status sent by the server, as a `ResponseStatusHTTP`"""
        return self._status

    @property
    def ok(self) -> bool:
        """Indicates whether the server has responded with a status code
        of **200 OK**, as a `bool`.
        """
        return self.status == StatusHTTP.OK

    @property
    def created(self) -> bool:
        """Indicates whether the server has responded with a status code
        of **201 Created**, as a `bool`.
        """
        return self.status == StatusHTTP.CREATED

    @property
    def not_found(self) -> bool:
        """Indicates whether the server has responded with a status code
        of **404 Not Found**, as a `bool`.
        """
        return self.status == StatusHTTP.NOT_FOUND

    def get_headers(self) -> dict[str, str]:
        """Gets the response headers.

        Returns:
            dict: The response HTTP headers sent by the server, as a
                mutable `dict` mapping `str` header names to
                header `str` values.
        """
        return self._headers

    def get_body(self) -> bytes:
        """Gets the raw undecoded response body.

        If the server has not responded with a body, this method returns
        an empty `bytes` object.

        Returns:
            bytes: The response HTTP body sent by the server.
        """
        return self._body if self._body is not None else b""

    def get_body_text(self) -> str:
        """Gets the decoded text response body.

        If the server has not responded with a body, this method returns
        an empty `str` object. The encoding of the raw body data is determined
        by the `charset` parameter of the `Content-Type` response header,
        defaulting to UTF-8 if absent.

        Returns:
            str: The response HTTP body sent by the server, decoded as text.

        Raises:
            UnicodeDecodeError: If the raw response body cannot be decoded.
        """
        if not self._body:
            return ""

        encoding = "UTF-8"
        content_type = self._headers.get("Content-Type", "")
        for part in content_type.split(";"):
            part = part.strip()
            if part.lower().startswith("charset="):
                encoding = part[8:].strip().strip('"')
                break

        return self._body.decode(encoding)

    def get_body_json(self) -> dict:
        """Gets the decoded JSON text response body.

        If the server has not responded with a body, this method returns
        an empty `dict` object.

        Returns:
            dict: The response HTTP body sent by the server, decoded as
                JSON and deserialised.

        Raises:
            ValueError: If the response body cannot be deserialised as JSON.
            JSONDecodeError: If the deserialized text body cannot
                be decoded as valid JSON.
        """
        content_type = self._headers.get("Content-Type")
        if content_type is None:
            raise ValueError("Unknown content type")

        media_type = content_type.split(";")[0].strip().lower()
        if media_type != "application/json":
            raise ValueError(
                "Cannot deserialise JSON of HTTP response "
                f"with content type '{content_type}'"
            )

        return json.loads(self.get_body_text())

    def __repr__(self):
        preview_size = 512
        body_size = len(self._body) if self._body is not None else 0
        body_preview = b"" if self._body is None else self._body[:preview_size]
        body_suffix = " [...] " if body_size > preview_size else ""
        return (
            "ResponseHTTP("
            f"status={self._status}, "
            f"headers={self._headers!r}, "
            f"body_size={body_size}, "
            f"body_preview={body_preview!r}{body_suffix}"
            ")"
        )


class RequestHTTP:
    """An HTTP request to be sent to a server."""

    # The default value for connection attempt timeouts, in milliseconds.
    DEFAULT_TIMEOUT: Final[int] = 5_000

    def __init__(self, method: MethodHTTP, url: URL):
        """Initializes a new `RequestHTTP` instance.

        Args:
            method (MethodHTTP): The HTTP method to use for the request.
            url (URL): The URL to send the request to.
        """
        self._method = method
        self._url = url
        self._headers: dict[str, str] = {}
        self._body = None
        self._timeout = RequestHTTP.DEFAULT_TIMEOUT

    @property
    def method(self) -> MethodHTTP:
        """The HTTP method of this request, as a `MethodHTTP`."""
        return self._method

    @property
    def url(self) -> URL:
        """The URL of this request, as a `URL` object."""
        return self._url

    @property
    def timeout(self) -> int:
        """The timeout for connection attempts, in milliseconds,
        as a non-negative `int`.
        """
        return self._timeout

    @timeout.setter
    def timeout(self, value: int):
        TypeCheck.require_prop(value, int, "timeout")
        if value < 0:
            raise ValueError(
                f"Request timeout value must not be negative: {value}"
            )

        self._timeout = value

    def get_headers(self) -> dict[str, str]:
        """Gets the request HTTP headers.

        Returns:
            dict: A copy of the HTTP headers of this request, as
                a `dict` mapping header names (`str`) to header
                values (`str`).
        """
        return self._headers.copy()

    def set_header(self, name: str, value: str):
        """Sets the request header with the specified name to
        the specified value.

        Args:
            name (str): The name of the header entry to set.
            value (str): The value of the header entry with the specified name.
        """
        self._headers[name] = value

    def get_body(self) -> Union[bytes, str, None]:
        """Gets the raw request body.

        Returns:
            The HTTP body of this request. The returned type is the type
                of what was set previously with `set_body()`.
        """
        return self._body

    def set_body(self, body: Union[bytes, str, None]):
        """Sets the request body.

        Args:
            body (bytes | str): The HTTP request body of the request.
                May be None.
        """
        self._body = body

    def set_json_body(self, data: dict):
        """Sets the request body as JSON-serialised data.

        Also sets the `Content-Type` header to `application/json`.

        Args:
            data (dict): The data to JSON-serialise and set
                as the request body.
        """
        self.set_body(json.dumps(data))
        self._headers["Content-Type"] = "application/json"

    def send(self) -> ResponseHTTP:
        """Sends this HTTP request.

        This is a convenience method and has exactly the same effect as
        creating a `ConnectionHTTP` object and calling `send()` on it with
        this request object as an argument.

        A call to this method may block until the response is fully received
        from the network counterparty or a connection timeout occurs.

        Returns:
            ResponseHTTP: The HTTP response to this sent request.

        Raises:
            ConnectionException: If this request cannot be sent to the
                receiving side.
        """
        http_connection = ConnectionHTTP.instance()
        http_response = http_connection.send(self)
        return http_response

    def __repr__(self):
        preview_size = 512
        body = self._body
        body_size = len(body) if isinstance(body, (str, bytes)) else 0
        if body is None:
            body_preview = None
            body_suffix = ""
        elif isinstance(body, (bytes, str)):
            body_preview = body[:preview_size]
            body_suffix = " [...] " if len(body) > preview_size else ""
        else:
            body_preview = body
            body_suffix = ""

        return (
            "RequestHTTP("
            f"method={self._method.value!r}, "
            f"url={str(self._url)!r}, "
            f"timeout={self._timeout}, "
            f"headers={self._headers!r}, "
            f"body_size={body_size}, "
            f"body_preview={body_preview!r}{body_suffix}"
            ")"
        )

    @classmethod
    def get(cls, url: URL) -> "RequestHTTP":
        """Creates a GET request for the specified URL."""
        return cls(MethodHTTP.GET, url)

    @classmethod
    def post(cls, url: URL) -> "RequestHTTP":
        """Creates a POST request for the specified URL."""
        return cls(MethodHTTP.POST, url)

    @classmethod
    def put(cls, url: URL) -> "RequestHTTP":
        """Creates a PUT request for the specified URL."""
        return cls(MethodHTTP.PUT, url)

    @classmethod
    def delete(cls, url: URL) -> "RequestHTTP":
        """Creates a DELETE request for the specified URL."""
        return cls(MethodHTTP.DELETE, url)

    @classmethod
    def patch(cls, url: URL) -> "RequestHTTP":
        """Creates a PATCH request for the specified URL."""
        return cls(MethodHTTP.PATCH, url)


@inject
class ConnectionHTTP(Interface):
    """Abstract class for sending HTTP requests over the network."""

    @abstractmethod
    def send(self, request: RequestHTTP) -> ResponseHTTP:
        """Sends an HTTP request.

        Implementations of this method must return a valid `ResponseHTTP`
        object or raise a `ConnectionException` if the request cannot be sent.

        Args:
            request (RequestHTTP): The request to send.

        Returns:
            ResponseHTTP: The received response.

        Raises:
            ConnectionException: If the specified request cannot be sent
                to the receiving side.
        """


class ClientAuthenticationHeader:
    """A Fathom-specific client authentication HTTP-header value.

    This class works with `ClientAuthentication` objects.
    Use the `encode()` and `decode()` methods to transform to and from
    HTTP header values, respectively.
    A Fathom client authentication HTTP-header value is the username
    and password, using the hex representation of the UTF-8 encoded string
    for each, concatenated via a colon (':'), as a base64-encoded string.

    For example, if the username is 'myuser1' and the password
    is 'mypassword1', the corresponding HTTP header value would be:
    'NmQ3OTc1NzM2NTcyMzE6NmQ3OTcwNjE3MzczNzc2ZjcyNjQzMQ=='
    """

    _FIELD_DELIM = ":"

    def __init__(self, value: Union[ClientAuthentication, str]):
        """Initializes a new `ClientAuthenticationHeader` instance.

        Args:
            value (ClientAuthentication, str): The header value either
                in an HTTP-header value encoded form (`str`),
                or a decoded `ClientAuthentication` object form.
        """
        self._obj = value
        if not isinstance(value, (ClientAuthentication, str)):
            raise TypeError(
                "Invalid argument. "
                f"Expected ClientAuthentication or str but found {type(value)}"
            )

    def encode(self) -> str:
        """Encodes this `ClientAuthenticationHeader` into a header string.

        Returns:
            str: A string to be used in an HTTP-header.

        Raises:
            HTTPEncodeException: If an encoding error occurs.
        """
        if isinstance(self._obj, ClientAuthentication):
            self._obj = self._encode_auth_obj()

        assert isinstance(self._obj, str)
        return self._obj

    def decode(self) -> ClientAuthentication:
        """Decodes this encoded `ClientAuthenticationHeader` into
        a `ClientAuthentication` object.

        Returns:
            ClientAuthentication: The decoded authentication HTTP-header.

        Raises:
            HTTPDecodeException: If a decoding error occurs.
        """
        if isinstance(self._obj, str):
            self._obj = self._decode_auth_string()

        assert isinstance(self._obj, ClientAuthentication)
        return self._obj

    def _encode_auth_obj(self):
        try:
            return self._encode_auth_obj_impl()
        except (ValueError, TypeError, UnicodeEncodeError) as error:
            raise HTTPEncodeException(
                "Failed to encode client authentication header: "
                f"Encountered an error of type {error.__class__}"
            ) from None

    def _encode_auth_obj_impl(self):
        assert isinstance(self._obj, ClientAuthentication)
        user = self._encode_auth_token(self._obj.username)
        if not user:
            raise HTTPEncodeException(
                "Failed to encode client authentication header: "
                "Username must not be empty"
            )

        password = self._encode_auth_token(self._obj.password)
        if not password:
            raise HTTPEncodeException(
                "Failed to encode client authentication header: "
                "Password must not be empty"
            )

        return self._encode_auth_data(
            f"{user}{ClientAuthenticationHeader._FIELD_DELIM}{password}"
        )

    def _encode_auth_token(self, token):
        return token.encode("UTF-8").hex()

    def _encode_auth_data(self, auth_value):
        return base64.b64encode(auth_value.encode("UTF-8")).decode("UTF-8")

    def _decode_auth_string(self):
        try:
            return self._decode_auth_string_impl()
        except (
            ValueError, TypeError, UnicodeEncodeError, binascii.Error
        ) as error:
            raise HTTPDecodeException(
                "Failed to decode client authentication header: "
                f"Encountered an error of type {error.__class__}"
            ) from None

    def _decode_auth_string_impl(self):
        data = self._decode_auth_data().split(
            ClientAuthenticationHeader._FIELD_DELIM,
            maxsplit=1
        )
        if len(data) != 2:
            raise HTTPDecodeException(
                "Failed to decode client authentication header: "
                "Malformed client authentication header value"
            )

        return ClientAuthentication(
            username=self._decode_auth_token(data[0]),
            password=self._decode_auth_token(data[1]),
        )

    def _decode_auth_token(self, token):
        return bytes.fromhex(token).decode("UTF-8")

    def _decode_auth_data(self):
        assert isinstance(self._obj, str)
        return base64.b64decode(
            self._obj.encode("UTF-8"),
            validate=True,
        ).decode("UTF-8")


class StatusHTTP(ResponseStatusHTTP, Enum):
    """Enumeration of standard HTTP response status codes."""

    def __new__(cls, code: StatusCodeHTTP, reason: str):
        obj = object.__new__(cls)
        obj._value_ = ResponseStatusHTTP(code, reason)
        return obj

    CONTINUE = 100, "Continue"

    SWITCHING_PROTOCOLS = 101, "Switching Protocols"

    PROCESSING = 102, "Processing"

    EARLY_HINTS = 103, "Early Hints"

    OK = 200, "OK"

    CREATED = 201, "Created"

    ACCEPTED = 202, "Accepted"

    NON_AUTHORITATIVE_INFORMATION = 203, "Non-Authoritative Information"

    NO_CONTENT = 204, "No Content"

    RESET_CONTENT = 205, "Reset Content"

    PARTIAL_CONTENT = 206, "Partial Content"

    MULTI_STATUS = 207, "Multi-Status"

    ALREADY_REPORTED = 208, "Already Reported"

    IM_USED = 226, "IM Used"

    MULTIPLE_CHOICES = 300, "Multiple Choices"

    MOVED_PERMANENTLY = 301, "Moved Permanently"

    FOUND = 302, "Found"

    SEE_OTHER = 303, "See Other"

    NOT_MODIFIED = 304, "Not Modified"

    USE_PROXY = 305, "Use Proxy"

    UNUSED = 306, "Unused"

    TEMPORARY_REDIRECT = 307, "Temporary Redirect"

    PERMANENT_REDIRECT = 308, "Permanent Redirect"

    BAD_REQUEST = 400, "Bad Request"

    UNAUTHORIZED = 401, "Unauthorized"

    PAYMENT_REQUIRED = 402, "Payment Required"

    FORBIDDEN = 403, "Forbidden"

    NOT_FOUND = 404, "Not Found"

    METHOD_NOT_ALLOWED = 405, "Method Not Allowed"

    NOT_ACCEPTABLE = 406, "Not Acceptable"

    PROXY_AUTHENTICATION_REQUIRED = 407, "Proxy Authentication Required"

    REQUEST_TIMEOUT = 408, "Request Timeout"

    CONFLICT = 409, "Conflict"

    GONE = 410, "Gone"

    LENGTH_REQUIRED = 411, "Length Required"

    PRECONDITION_FAILED = 412, "Precondition Failed"

    CONTENT_TOO_LARGE = 413, "Content Too Large"

    URI_TOO_LONG = 414, "URI Too Long"

    UNSUPPORTED_MEDIA_TYPE = 415, "Unsupported Media Type"

    RANGE_NOT_SATISFIABLE = 416, "Range Not Satisfiable"

    EXPECTATION_FAILED = 417, "Expectation Failed"

    IM_A_TEAPOT = 418, "I'm a teapot"

    I_AM_A_TEAPOT = IM_A_TEAPOT

    MISDIRECTED_REQUEST = 421, "Misdirected Request"

    UNPROCESSABLE_CONTENT = 422, "Unprocessable Content"

    LOCKED = 423, "Locked"

    FAILED_DEPENDENCY = 424, "Failed Dependency"

    TOO_EARLY = 425, "Too Early"

    UPGRADE_REQUIRED = 426, "Upgrade Required"

    PRECONDITION_REQUIRED = 428, "Precondition Required"

    TOO_MANY_REQUESTS = 429, "Too Many Requests"

    REQUEST_HEADER_FIELDS_TOO_LARGE = 431, "Request Header Fields Too Large"

    UNAVAILABLE_FOR_LEGAL_REASONS = 451, "Unavailable For Legal Reasons"

    INTERNAL_SERVER_ERROR = 500, "Internal Server Error"

    NOT_IMPLEMENTED = 501, "Not Implemented"

    BAD_GATEWAY = 502, "Bad Gateway"

    SERVICE_UNAVAILABLE = 503, "Service Unavailable"

    GATEWAY_TIMEOUT = 504, "Gateway Timeout"

    HTTP_VERSION_NOT_SUPPORTED = 505, "HTTP Version Not Supported"

    VARIANT_ALSO_NEGOTIATES = 506, "Variant Also Negotiates"

    INSUFFICIENT_STORAGE = 507, "Insufficient Storage"

    LOOP_DETECTED = 508, "Loop Detected"

    NOT_EXTENDED = 510, "Not Extended"

    NETWORK_AUTHENTICATION_REQUIRED = 511, "Network Authentication Required"
