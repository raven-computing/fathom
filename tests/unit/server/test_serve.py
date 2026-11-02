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
"""Unit tests for the server serve command."""

from unittest.mock import patch

from raven.fathom.base import Configuration, ConfigurationSection
from raven.fathom.server.cli.arguments import AppArgs
from raven.fathom.server.cli.serve import ServeCommand
from raven.fathom.server.core.config import ConfigurationManager
from raven.fathom.server.core.config import ServerConfiguration
from raven.fathom.server.net.http.application import ServerApplication
from raven.fathom.server.net.http.server import ServerHTTP
from raven.fathom.server.net.defaults import DEFAULT_SERVER_ADDRESS_LISTEN
from raven.fathom.server.net.defaults import DEFAULT_SERVER_PORT

from tests.unit import TestCase
from tests.unit.mocks import Mock


class TestServeCommand(TestCase):
    """Unit tests for the `ServeCommand` class."""

    def setUp(self):
        super().setUp()
        self.config = Configuration()
        self.config.add_section(
            ConfigurationSection(ServerConfiguration.SERVER)
        )
        self.config.set_value(
            ServerConfiguration.SERVER.ADDRESS_LISTEN,
            DEFAULT_SERVER_ADDRESS_LISTEN
        )
        self.config.set_value(
            ServerConfiguration.SERVER.PORT_LISTEN,
            DEFAULT_SERVER_PORT
        )

    def test_execute_starts_and_runs_server(self):
        command = ServeCommand(AppArgs())
        mock_status = 42

        with patch.object(
            ConfigurationManager,
            "get_server_config",
            return_value=self.config,
        ), patch.object(ServerHTTP, "start"), patch.object(
            ServerHTTP,
            "run",
            autospec=True,
        ) as run_mock, patch.object(
            ServerHTTP,
            "status_code",
            return_value=mock_status,
        ):
            status = command.execute()

        self.assertEqual(status, mock_status)
        run_mock.assert_called_once()

    def test_server_is_started_on_configured_port(self):
        mock_addr = "42.42.42.42"
        mock_port = 42
        self.config[ServerConfiguration.SERVER.ADDRESS_LISTEN] = mock_addr
        self.config[ServerConfiguration.SERVER.PORT_LISTEN] = mock_port

        server = ServerHTTP(Mock(spec_set=ServerApplication), self.config)

        self.assertEqual(server.address, mock_addr)
        self.assertEqual(server.port, mock_port)


if __name__ == "__main__":
    TestCase.run_tests()
