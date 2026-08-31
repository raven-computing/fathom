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
"""Integration tests for the HTTP client implementation."""

# pylint: disable=C0116,C0103

import json
import threading

from http.server import BaseHTTPRequestHandler, HTTPServer

from raven.fathom.base._net_http import ConnectionHTTPImpl
from raven.fathom.base.http import (
    ConnectionHTTP,
    ConnectionException,
    MethodHTTP,
    RequestHTTP,
    ResponseHTTP,
)
from raven.fathom.base import URL
from raven.fathom.base import OperatingSystem
from raven.fathom.base._env import HostSystemEnvironment

from tests.integration import TestCase


class _LocalHTTPRequestHandler(BaseHTTPRequestHandler):
    """A minimal HTTP request handler used by the local test server."""

    def log_message(self, format, *args): # pylint: disable=W0622
        # Suppress default request logging to keep test output clean.
        pass

    def do_GET(self):
        if self.path == "/":
            body = b"Hello, World!"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=UTF-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/json":
            body = json.dumps({"status": "ok"}).encode("UTF-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/echo-headers":
            # Reflect selected request headers back as a JSON body.
            echoed = {
                k: v for k, v in self.headers.items()
                if k.lower().startswith("x-test-")
            }
            body = json.dumps(echoed).encode("UTF-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/created":
            self.send_response(201)
            self.send_header("Content-Length", "0")
            self.end_headers()
        elif self.path == "/not-found":
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()
        elif self.path == "/error":
            self.send_response(500)
            self.send_header("Content-Length", "0")
            self.end_headers()
        else:
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()

    def do_HEAD(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=UTF-8")
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/echo":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()

    def do_PUT(self):
        self.send_response(200)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_DELETE(self):
        self.send_response(200)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_PATCH(self):
        self.send_response(200)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_TRACE(self):
        self.send_response(200)
        self.send_header("Content-Length", "0")
        self.end_headers()


class TestConnectionHTTPImpl(TestCase):
    """Integration tests for the `ConnectionHTTPImpl` class.

    This integration test case uses a local embedded HTTP server started
    on a loopback interface to verify that the real HTTP client
    implementation performs correct network I/O.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._server = HTTPServer(("127.0.0.1", 0), _LocalHTTPRequestHandler)
        port = cls._server.server_address[1]
        cls._base_url = f"http://127.0.0.1:{port}"
        cls._server_thread = threading.Thread(
            target=cls._server.serve_forever,
            daemon=True,
        )
        cls._server_thread.start()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls._server.shutdown()
        cls._server.server_close()

    def setUp(self):
        super().setUp()
        self.connection = ConnectionHTTPImpl()

    def url(self, path: str) -> URL:
        return URL(self._base_url + path)

    def test_default_implementation_is_connection_http_impl(self):
        instance = ConnectionHTTP.instance()
        self.assertIsNotNone(instance)
        self.assertIsInstance(
            instance,
            ConnectionHTTPImpl,
            "Implementation detail: The default implementation provided for "
            "the ConnectionHTTP interface was expected to be "
            f"ConnectionHTTPImpl but found {type(instance)}. "
            "If this implementation detail was intentionally changed, "
            "please confirm by adjusting the test case."
        )

    def test_get_request_returns_successful_response(self):
        request = RequestHTTP.get(self.url("/"))
        response = self.connection.send(request)
        self.assertIsInstance(response, ResponseHTTP)
        self.assertTrue(response.ok)
        self.assertEqual(response.status_code, 200)

    def test_get_request_response_has_body_as_bytes(self):
        request = RequestHTTP.get(self.url("/"))
        response = self.connection.send(request)
        body = response.get_body()
        self.assertIsInstance(body, bytes)
        self.assertEqual(body, b"Hello, World!")

    def test_get_request_response_body_as_text(self):
        request = RequestHTTP.get(self.url("/"))
        response = self.connection.send(request)
        self.assertEqual(response.get_body_text(), "Hello, World!")

    def test_get_request_response_has_headers(self):
        request = RequestHTTP.get(self.url("/"))
        response = self.connection.send(request)
        headers = response.get_headers()
        self.assertIsInstance(headers, dict)
        self.assertGreater(len(headers), 0)

    def test_get_request_json_response_body(self):
        request = RequestHTTP.get(self.url("/json"))
        response = self.connection.send(request)
        self.assertEqual(response.status_code, 200)
        body = response.get_body_json()
        self.assertIsInstance(body, dict)
        self.assertEqual(body.get("status"), "ok")

    def test_post_request_body_is_echoed(self):
        request = RequestHTTP.post(self.url("/echo"))
        request.set_body(b"test-body")
        response = self.connection.send(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_body(), b"test-body")

    def test_post_request_with_json_body(self):
        payload = {"key": "value", "count": 42}
        request = RequestHTTP.post(self.url("/echo"))
        request.set_json_body(payload)
        response = self.connection.send(request)
        self.assertEqual(response.status_code, 200)
        echoed = json.loads(response.get_body())
        self.assertEqual(echoed, payload)

    def test_http_404_response_is_returned_not_raised(self):
        request = RequestHTTP(MethodHTTP.GET, self.url("/not-found"))
        response = self.connection.send(request)
        self.assertIsInstance(response, ResponseHTTP)
        self.assertTrue(response.not_found)
        self.assertEqual(response.status_code, 404)

    def test_http_500_response_is_returned_not_raised(self):
        request = RequestHTTP.get(self.url("/error"))
        response = self.connection.send(request)
        self.assertIsInstance(response, ResponseHTTP)
        self.assertTrue(response.server_error)
        self.assertEqual(response.status_code, 500)

    def test_head_request_returns_successful_response(self):
        request = RequestHTTP(MethodHTTP.HEAD, self.url("/"))
        response = self.connection.send(request)
        self.assertIsInstance(response, ResponseHTTP)
        self.assertEqual(response.status_code, 200)

    def test_put_request_returns_successful_response(self):
        request = RequestHTTP.put(self.url("/resource"))
        response = self.connection.send(request)
        self.assertIsInstance(response, ResponseHTTP)
        self.assertEqual(response.status_code, 200)

    def test_delete_request_returns_successful_response(self):
        request = RequestHTTP.delete(self.url("/resource"))
        response = self.connection.send(request)
        self.assertIsInstance(response, ResponseHTTP)
        self.assertEqual(response.status_code, 200)

    def test_patch_request_returns_successful_response(self):
        request = RequestHTTP.patch(self.url("/resource"))
        response = self.connection.send(request)
        self.assertIsInstance(response, ResponseHTTP)
        self.assertEqual(response.status_code, 200)

    def test_options_request_returns_successful_response(self):
        request = RequestHTTP(MethodHTTP.OPTIONS, self.url("/"))
        response = self.connection.send(request)
        self.assertIsInstance(response, ResponseHTTP)
        self.assertEqual(response.status_code, 200)

    def test_trace_request_returns_successful_response(self):
        request = RequestHTTP(MethodHTTP.TRACE, self.url("/"))
        response = self.connection.send(request)
        self.assertIsInstance(response, ResponseHTTP)
        self.assertEqual(response.status_code, 200)

    def test_connection_to_unreachable_host_raises_connection_exception(self):
        # Use port 1 which is a privileged port, so a connection
        # attempt to it will be refused immediately.
        request = RequestHTTP.get(URL("http://127.0.0.1:1/"))
        request.timeout = 3_000
        with self.assertRaises(ConnectionException) as raised:
            self.connection.send(request)

        detected_os = HostSystemEnvironment().get_operating_system()
        msg = (
            "No connection could be made "
            "because the target machine actively refused it"
            if detected_os == OperatingSystem.MS_WINDOWS
            else "Connection refused"
        )
        self.assertIn(msg, str(raised.exception))

    def test_get_request_with_custom_headers_are_sent_to_server(self):
        # The local server echoes back any header whose name starts with
        # 'X-Test-' as a JSON body so we can assert they were received.
        request = RequestHTTP.get(self.url("/echo-headers"))
        request.set_header("X-Test-Foo", "bar")
        request.set_header("X-Test-Answer", "42")
        response = self.connection.send(request)
        self.assertEqual(response.status_code, 200)
        echoed = response.get_body_json()
        # HTTP header names are case-insensitive; compare lower-case keys.
        echoed_lower = {k.lower(): v for k, v in echoed.items()}
        self.assertEqual(echoed_lower.get("x-test-foo"), "bar")
        self.assertEqual(echoed_lower.get("x-test-answer"), "42")

    def test_response_has_created_status_when_server_responds_201(self):
        request = RequestHTTP.get(self.url("/created"))
        response = self.connection.send(request)
        self.assertIsInstance(response, ResponseHTTP)
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.created)
        self.assertFalse(response.ok)

    def test_get_body_json_raises_value_error_on_non_json_content_type(self):
        request = RequestHTTP.get(self.url("/"))
        response = self.connection.send(request)
        self.assertEqual(response.status_code, 200)
        with self.assertRaises(ValueError) as raised:
            response.get_body_json()

        self.assertIn(
            "cannot deserialise json of http response with content type",
            str(raised.exception).lower()
        )

    def test_get_body_returns_empty_bytes_when_body_is_absent(self):
        request = RequestHTTP.get(self.url("/not-found"))
        response = self.connection.send(request)
        self.assertEqual(response.status_code, 404)
        body = response.get_body()
        self.assertIsInstance(body, bytes)
        self.assertEqual(body, b"")

    def test_get_body_text_returns_empty_string_when_body_is_absent(self):
        request = RequestHTTP.get(self.url("/not-found"))
        response = self.connection.send(request)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_body_text(), "")

    def test_server_error_property_is_false_for_non_5xx_response(self):
        request = RequestHTTP.get(self.url("/not-found"))
        response = self.connection.send(request)
        self.assertFalse(response.server_error)

    def test_not_found_property_is_false_for_non_404_response(self):
        request = RequestHTTP.get(self.url("/"))
        response = self.connection.send(request)
        self.assertFalse(response.not_found)


if __name__ == "__main__":
    TestCase.run_tests()
