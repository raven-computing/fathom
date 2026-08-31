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
"""Unit tests for the server_info module."""

from unittest.mock import patch

from raven.fathom.base import ClientRequest, Interaction, ServerResponse
from raven.fathom.server.version import Version
from raven.fathom.server.handlers.server_info import ServerInfoHandler

from tests.unit import TestCase


_VERSION_MODULE = "raven.fathom.server.handlers.server_info.Version"


class TestServerInfoHandler(TestCase):
    """Unit tests for the `ServerInfoHandler` class."""

    def setUp(self):
        super().setUp()
        self.request = ClientRequest(Interaction.QUERY_SERVER_INFO)
        self.response = ServerResponse(Interaction.QUERY_SERVER_INFO)
        self.handler = ServerInfoHandler()
        self._mock_version = Version(1, 2, 3)

    def _handle(self):
        with patch(f"{_VERSION_MODULE}.current",
                   return_value=self._mock_version):

            self.handler.handle(self.request, self.response)

    def test_handle_sets_server_info_in_response(self):
        self._handle()
        self.assertIsNotNone(self.response.server_info)
        self.assertIsInstance(self.response.server_info, dict)

    def test_handle_sets_server_agent_key(self):
        self._handle()
        self.assertIsNotNone(self.response.server_info)
        assert self.response.server_info is not None
        self.assertIn("server_agent", self.response.server_info)

    def test_handle_sets_correct_server_agent_name(self):
        self._handle()
        self.assertIsNotNone(self.response.server_info)
        assert self.response.server_info is not None
        self.assertEqual(
            self.response.server_info["server_agent"],
            "raven-fathom-server",
        )

    def test_handle_sets_app_version_key(self):
        self._handle()
        self.assertIsNotNone(self.response.server_info)
        assert self.response.server_info is not None
        self.assertIn("app_version", self.response.server_info)

    def test_handle_sets_app_version_as_string(self):
        self._handle()
        self.assertIsNotNone(self.response.server_info)
        assert self.response.server_info is not None
        self.assertIsInstance(self.response.server_info["app_version"], str)

    def test_handle_uses_version_string_when_version_available(self):
        self._handle()
        self.assertIsNotNone(self.response.server_info)
        assert self.response.server_info is not None
        self.assertEqual(self.response.server_info["app_version"], "1.2.3")

    def test_handle_sets_empty_app_version_when_version_unavailable(self):
        with patch(f"{_VERSION_MODULE}.current", return_value=None):
            self.handler.handle(self.request, self.response)

        self.assertIsNotNone(self.response.server_info)
        assert self.response.server_info is not None
        self.assertEqual(self.response.server_info["app_version"], "")
