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
"""Functionality tests for the publicly available endpoints."""

from raven.fathom.base import MethodHTTP
from raven.fathom.base import read_version_file
from raven.fathom.base.context import get_project_source_root

from tests.functionality import TestCase


class TestPublicEndpoints(TestCase):
    """Functionality test case to test that the public endpoints work.

    The public endpoints require no client authentication and are accessible
    to any HTTP client. Tests here verify the response structure, field types,
    and correctness of each public endpoint, as well as correct handling of
    unsupported methods and unknown paths.
    """

    def test_server_responds_with_correct_version_identifier(self):
        response = self.http(MethodHTTP.GET, "/public/server-version").send()

        self.assertEqual(200, response.status_code)
        json_response = response.get_body_json()
        self.assertIn("serverVersion", json_response)
        expected_version = str(
            read_version_file(get_project_source_root()) # type: ignore
        )
        actual_version = json_response["serverVersion"]["identifier"]
        self.assertEqual(expected_version, actual_version)
        self.assertTrue(self.server.is_running())

    def test_server_version_response_contains_complete_fields(self):
        response = self.http(MethodHTTP.GET, "/public/server-version").send()

        self.assertEqual(200, response.status_code)
        json_response = response.get_body_json()

        self.assertIn("status", json_response)
        self.assertEqual("OK", json_response["status"])

        self.assertIn("serverVersion", json_response)
        version = json_response["serverVersion"]
        self.assertIn("identifier", version)
        self.assertIsInstance(version["identifier"], str)
        self.assertGreater(len(version["identifier"]), 0)

        self.assertIn("major", version)
        self.assertIsInstance(version["major"], int)

        self.assertIn("minor", version)
        self.assertIsInstance(version["minor"], int)

        self.assertIn("patch", version)
        self.assertIsInstance(version["patch"], int)

        self.assertIn("isDevelopmentVersion", json_response)
        self.assertIsInstance(json_response["isDevelopmentVersion"], bool)

    def test_server_rejects_non_get_method_on_version_endpoint(self):
        response = self.http(MethodHTTP.POST, "/public/server-version").send()

        self.assertEqual(405, response.status_code)

    def test_server_returns_404_for_unknown_endpoint(self):
        response = self.http(MethodHTTP.GET, "/public/nonexistent").send()

        self.assertEqual(404, response.status_code)


if __name__ == "__main__":
    TestCase.run_tests()
