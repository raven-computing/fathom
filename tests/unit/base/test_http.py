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
"""Unit tests for the base http module."""

import json

from raven.fathom.base.testing import ConnectionHTTPMock
from raven.fathom.base.http import ClientAuthenticationHeader
from raven.fathom.base.http import MethodHTTP, RequestHTTP, ResponseHTTP
from raven.fathom.base.http import HTTPEncodeException, HTTPDecodeException
from raven.fathom.base.http import ConnectionException
from raven.fathom.base.authentication import ClientAuthentication
from raven.fathom.base.url import URL

from tests.unit import TestCase


SPECIAL_CHARS = (
    r"( 2 < F P Z d n x ) 3 = G Q [ e o y * 4 > H R \ f p z ! + 5 ? I S ] g q "
    r"{ \" , 6 @ J T ^ h r | # - 7 A K U _ i s } $ . 8 B L V \` j t ~ % / 9 C "
    r"M W a k u & 0 : D N X b l v ' 1 ; E O Y c m w"
)
SPECIAL_CHARS_REVERSED = "".join(reversed(list(SPECIAL_CHARS)))
SPECIAL_CHAR_ENCODED_HEADER = (
    "MjgyMDMyMjAzYzIwNDYyMDUwMjA1YTIwNjQyMDZlMjA3ODIwMjkyMDMzMjAzZDIw"
    "NDcyMDUxMjA1YjIwNjUyMDZmMjA3OTIwMmEyMDM0MjAzZTIwNDgyMDUyMjA1YzIw"
    "NjYyMDcwMjA3YTIwMjEyMDJiMjAzNTIwM2YyMDQ5MjA1MzIwNWQyMDY3MjA3MTIw"
    "N2IyMDVjMjIyMDJjMjAzNjIwNDAyMDRhMjA1NDIwNWUyMDY4MjA3MjIwN2MyMDIz"
    "MjAyZDIwMzcyMDQxMjA0YjIwNTUyMDVmMjA2OTIwNzMyMDdkMjAyNDIwMmUyMDM4"
    "MjA0MjIwNGMyMDU2MjA1YzYwMjA2YTIwNzQyMDdlMjAyNTIwMmYyMDM5MjA0MzIw"
    "NGQyMDU3MjA2MTIwNmIyMDc1MjAyNjIwMzAyMDNhMjA0NDIwNGUyMDU4MjA2MjIw"
    "NmMyMDc2MjAyNzIwMzEyMDNiMjA0NTIwNGYyMDU5MjA2MzIwNmQyMDc3Ojc3MjA2"
    "ZDIwNjMyMDU5MjA0ZjIwNDUyMDNiMjAzMTIwMjcyMDc2MjA2YzIwNjIyMDU4MjA0"
    "ZTIwNDQyMDNhMjAzMDIwMjYyMDc1MjA2YjIwNjEyMDU3MjA0ZDIwNDMyMDM5MjAy"
    "ZjIwMjUyMDdlMjA3NDIwNmEyMDYwNWMyMDU2MjA0YzIwNDIyMDM4MjAyZTIwMjQy"
    "MDdkMjA3MzIwNjkyMDVmMjA1NTIwNGIyMDQxMjAzNzIwMmQyMDIzMjA3YzIwNzIy"
    "MDY4MjA1ZTIwNTQyMDRhMjA0MDIwMzYyMDJjMjAyMjVjMjA3YjIwNzEyMDY3MjA1"
    "ZDIwNTMyMDQ5MjAzZjIwMzUyMDJiMjAyMTIwN2EyMDcwMjA2NjIwNWMyMDUyMjA0"
    "ODIwM2UyMDM0MjAyYTIwNzkyMDZmMjA2NTIwNWIyMDUxMjA0NzIwM2QyMDMzMjAy"
    "OTIwNzgyMDZlMjA2NDIwNWEyMDUwMjA0NjIwM2MyMDMyMjAyOA=="
)


class TestClientAuthenticationHeader(TestCase):
    """Unit tests for the `ClientAuthenticationHeader` class.

    Tests that encoding and decoding works properly.
    """

    def test_encode_client_authentication_header(self):
        auth = ClientAuthentication(
            username="My-Username",
            password="My-Password-123456"
        )
        encoded_header_value = ClientAuthenticationHeader(auth).encode()
        self.assertIsInstance(encoded_header_value, str)
        self.assertEqual(
            encoded_header_value,
            "NGQ3OTJkNTU3MzY1NzI2ZTYxNmQ2NTo0ZDc5MmQ"
            "1MDYxNzM3Mzc3NmY3MjY0MmQzMTMyMzMzNDM1MzY="
        )

    def test_decode_client_authentication_header(self):
        auth_header = (
            "NGQ3OTJkNTU3MzY1NzI2ZTYxNmQ2NTo0ZDc5MmQ"
            "1MDYxNzM3Mzc3NmY3MjY0MmQzMTMyMzMzNDM1MzY="
        )
        client_auth = ClientAuthenticationHeader(auth_header).decode()
        self.assertIsInstance(client_auth, ClientAuthentication)
        self.assertEqual(client_auth.username, "My-Username")
        self.assertEqual(client_auth.password, "My-Password-123456")

    def test_encode_with_special_characters(self):
        auth = ClientAuthentication(
            username=SPECIAL_CHARS,
            password=SPECIAL_CHARS_REVERSED,
        )
        encoded_header_value = ClientAuthenticationHeader(auth).encode()
        self.assertIsInstance(encoded_header_value, str)
        self.assertEqual(encoded_header_value, SPECIAL_CHAR_ENCODED_HEADER)

    def test_decode_with_special_characters(self):
        auth_header = SPECIAL_CHAR_ENCODED_HEADER
        client_auth = ClientAuthenticationHeader(auth_header).decode()
        self.assertIsInstance(client_auth, ClientAuthentication)
        self.assertEqual(client_auth.username, SPECIAL_CHARS)
        self.assertEqual(client_auth.password, SPECIAL_CHARS_REVERSED)

    def test_encode_auth_with_empty_username_raises_exception(self):
        auth = ClientAuthentication(
            username="",
            password="My-Password"
        )
        with self.assertRaises(HTTPEncodeException) as raised:
            ClientAuthenticationHeader(auth).encode()

        self.assertIn("Username must not be empty", str(raised.exception))

    def test_encode_auth_with_empty_password_raises_exception(self):
        auth = ClientAuthentication(
            username="My-Username",
            password=""
        )
        with self.assertRaises(HTTPEncodeException) as raised:
            ClientAuthenticationHeader(auth).encode()

        self.assertIn("Password must not be empty", str(raised.exception))

    def test_decode_malformed_auth_header_value_raises_exception(self):
        malformed_auth_header = (
            "NGQ3OTJkNTU3MzY1NzI2ZTYxNmQ2NTRkNzkyZDU"
            "wNjE3MzczNzc2ZjcyNjQyZDMxMzIzMzM0MzUzNg=="
        )
        with self.assertRaises(HTTPDecodeException) as raised:
            ClientAuthenticationHeader(malformed_auth_header).decode()

        self.assertIn(
            "Failed to decode client authentication header",
            str(raised.exception)
        )
        self.assertIn(
            "Malformed client authentication header value",
            str(raised.exception)
        )

    def test_decode_auth_header_with_invalid_base64_char_raises_ex(self):
        invalid_char = "ß"
        auth_header = invalid_char + (
            "NGQ3OTJkNTU3MzY1NzI2ZTYxNmQ2NTRkNzkyZDU"
            "wNjE3MzczNzc2ZjcyNjQyZDMxMzIzMzM0MzUzNg=="
        )
        with self.assertRaises(HTTPDecodeException) as raised:
            ClientAuthenticationHeader(auth_header).decode()

        self.assertIn(
            "Failed to decode client authentication header",
            str(raised.exception)
        )


class TestRequestHTTP(TestCase):
    """Unit tests for the `RequestHTTP` class."""

    def setUp(self):
        super().setUp()
        self.url = URL("http://example.com/api")

    def test_method_property(self):
        request = RequestHTTP(MethodHTTP.GET, self.url)
        self.assertEqual(request.method, MethodHTTP.GET)

    def test_url_property(self):
        request = RequestHTTP(MethodHTTP.POST, self.url)
        self.assertEqual(request.url, self.url)

    def test_timeout_default_value(self):
        request = RequestHTTP(MethodHTTP.GET, self.url)
        self.assertEqual(request.timeout, RequestHTTP.DEFAULT_TIMEOUT)
        self.assertEqual(request.timeout, 5_000)

    def test_timeout_setter_updates_value(self):
        request = RequestHTTP(MethodHTTP.GET, self.url)
        request.timeout = 10_000
        self.assertEqual(request.timeout, 10_000)

    def test_timeout_setter_accepts_zero(self):
        request = RequestHTTP(MethodHTTP.GET, self.url)
        request.timeout = 0
        self.assertEqual(request.timeout, 0)

    def test_timeout_setter_raises_on_negative_value(self):
        request = RequestHTTP(MethodHTTP.GET, self.url)
        with self.assertRaises(ValueError):
            request.timeout = -1

    def test_get_headers_returns_empty_dict_initially(self):
        request = RequestHTTP(MethodHTTP.GET, self.url)
        self.assertEqual(request.get_headers(), {})

    def test_set_and_get_header(self):
        request = RequestHTTP(MethodHTTP.GET, self.url)
        request.set_header("Accept", "application/json")
        self.assertEqual(request.get_headers()["Accept"], "application/json")

    def test_get_headers_returns_copy(self):
        request = RequestHTTP(MethodHTTP.GET, self.url)
        request.set_header("X-Test", "value")
        headers = request.get_headers()
        headers["X-Extra"] = "extra"
        self.assertNotIn("X-Extra", request.get_headers())

    def test_get_body_returns_none_initially(self):
        request = RequestHTTP(MethodHTTP.GET, self.url)
        self.assertIsNone(request.get_body())

    def test_set_body_bytes(self):
        request = RequestHTTP(MethodHTTP.POST, self.url)
        body = b"raw bytes"
        request.set_body(body)
        self.assertEqual(request.get_body(), body)

    def test_set_body_string(self):
        request = RequestHTTP(MethodHTTP.POST, self.url)
        body = "text body"
        request.set_body(body)
        self.assertEqual(request.get_body(), body)

    def test_set_body_none(self):
        request = RequestHTTP(MethodHTTP.POST, self.url)
        request.set_body(b"data")
        request.set_body(None)
        self.assertIsNone(request.get_body())

    def test_set_json_body_serialises_data(self):
        request = RequestHTTP(MethodHTTP.POST, self.url)
        data = {"key": "value", "num": 1}
        request.set_json_body(data)
        body = request.get_body()
        self.assertIsNotNone(body)
        self.assertIsInstance(body, str)
        body_obj = json.loads(body) # type: ignore
        self.assertEqual(body_obj, data)

    def test_set_json_body_sets_content_type_header(self):
        request = RequestHTTP(MethodHTTP.POST, self.url)
        request.set_json_body({"key": "value"})
        self.assertEqual(
            request.get_headers()["Content-Type"],
            "application/json"
        )

    def test_send_uses_connection_http_instance(self):
        connection = ConnectionHTTPMock()
        expected_response = ResponseHTTP(200, {}, b"ok")
        connection.default_response = expected_response
        request = RequestHTTP(MethodHTTP.POST, self.url)
        response = request.send()
        self.assertIsInstance(response, ResponseHTTP)
        self.assertIs(response, expected_response)
        self.assertIs(connection.sent_requests[0], request)

    def test_send_raises_connection_exception_on_failure(self):
        connection = ConnectionHTTPMock()
        connection.raise_on_send = ConnectionException("Connection failed")
        request = RequestHTTP(MethodHTTP.GET, self.url)
        with self.assertRaises(ConnectionException) as raised:
            request.send()

        self.assertIn("Connection failed", str(raised.exception))

    def test_get_classmethod_creates_get_request(self):
        url = self.url
        request = RequestHTTP.get(url)
        self.assertEqual(request.method, MethodHTTP.GET)
        self.assertEqual(request.url, url)

    def test_post_classmethod_creates_post_request(self):
        url = self.url
        request = RequestHTTP.post(url)
        self.assertEqual(request.method, MethodHTTP.POST)
        self.assertEqual(request.url, url)

    def test_put_classmethod_creates_put_request(self):
        url = self.url
        request = RequestHTTP.put(url)
        self.assertEqual(request.method, MethodHTTP.PUT)
        self.assertEqual(request.url, url)

    def test_delete_classmethod_creates_delete_request(self):
        url = self.url
        request = RequestHTTP.delete(url)
        self.assertEqual(request.method, MethodHTTP.DELETE)
        self.assertEqual(request.url, url)

    def test_patch_classmethod_creates_patch_request(self):
        url = self.url
        request = RequestHTTP.patch(url)
        self.assertEqual(request.method, MethodHTTP.PATCH)
        self.assertEqual(request.url, url)


class TestResponseHTTP(TestCase):
    """Unit tests for the `ResponseHTTP` class."""

    def test_status_code_property(self):
        response = ResponseHTTP(200, {}, None)
        self.assertEqual(response.status_code, 200)

    def test_ok_is_true_for_200(self):
        response = ResponseHTTP(200, {}, None)
        self.assertTrue(response.ok)

    def test_ok_is_false_for_non_200(self):
        self.assertFalse(ResponseHTTP(201, {}, None).ok)
        self.assertFalse(ResponseHTTP(404, {}, None).ok)
        self.assertFalse(ResponseHTTP(500, {}, None).ok)

    def test_created_is_true_for_201(self):
        response = ResponseHTTP(201, {}, None)
        self.assertTrue(response.created)

    def test_created_is_false_for_non_201(self):
        self.assertFalse(ResponseHTTP(200, {}, None).created)
        self.assertFalse(ResponseHTTP(404, {}, None).created)

    def test_not_found_is_true_for_404(self):
        response = ResponseHTTP(404, {}, None)
        self.assertTrue(response.not_found)

    def test_not_found_is_false_for_non_404(self):
        self.assertFalse(ResponseHTTP(200, {}, None).not_found)
        self.assertFalse(ResponseHTTP(500, {}, None).not_found)

    def test_server_error_is_true_for_5xx(self):
        for code in (500, 503, 599):
            self.assertTrue(ResponseHTTP(code, {}, None).server_error)

    def test_server_error_is_false_for_non_5xx(self):
        for code in (200, 201, 404, 499):
            self.assertFalse(ResponseHTTP(code, {}, None).server_error)

    def test_get_headers_returns_headers_dict(self):
        headers = {"Content-Type": "application/json", "X-Custom": "value"}
        response = ResponseHTTP(200, headers, None)
        self.assertEqual(response.get_headers(), headers)

    def test_get_body_returns_empty_bytes_when_no_body(self):
        response = ResponseHTTP(200, {}, None)
        self.assertEqual(response.get_body(), b"")

    def test_get_body_returns_body_bytes(self):
        body = b"Hello, World!"
        response = ResponseHTTP(200, {}, body)
        self.assertEqual(response.get_body(), body)

    def test_get_body_text_returns_empty_string_when_no_body(self):
        response = ResponseHTTP(200, {}, None)
        self.assertEqual(response.get_body_text(), "")

    def test_get_body_text_decodes_utf8_by_default(self):
        text = "Hello, World!"
        response = ResponseHTTP(200, {}, text.encode("UTF-8"))
        self.assertEqual(response.get_body_text(), text)

    def test_get_body_text_uses_charset_from_content_type_header(self):
        text = "Héllo"
        headers = {"Content-Type": "text/plain; charset=UTF-8"}
        response = ResponseHTTP(200, headers, text.encode("UTF-8"))
        self.assertEqual(response.get_body_text(), text)

    def test_get_body_json_returns_parsed_dict(self):
        data = {"key": "value", "number": 42}
        headers = {"Content-Type": "application/json"}
        response = ResponseHTTP(200, headers, json.dumps(data).encode("UTF-8"))
        self.assertEqual(response.get_body_json(), data)

    def test_get_body_json_raises_when_no_content_type_header(self):
        response = ResponseHTTP(200, {}, b'{"key": "value"}')
        with self.assertRaises(ValueError):
            response.get_body_json()

    def test_get_body_json_raises_when_wrong_content_type(self):
        headers = {"Content-Type": "text/plain"}
        response = ResponseHTTP(200, headers, b'{"key": "value"}')
        with self.assertRaises(ValueError):
            response.get_body_json()


if __name__ == "__main__":
    TestCase.run_tests()
