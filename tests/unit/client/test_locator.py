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
"""Unit tests for the client locator module."""

from raven.fathom.base import Configuration, ConfigurationSection
from raven.fathom.client.locator import ServerLocator, load_server_locator
from raven.fathom.client.config import UserConfiguration, ProjectConfiguration
from raven.fathom.client.exceptions import InvalidConfigurationException
from raven.fathom.client.cli.arguments import ArgumentsCLI

from tests.unit import TestCase
from tests.fixtures import ConfigurationFixture


class TestServerLocator(TestCase):
    """Tests the `ServerLocator` class."""

    def test_initializer_accepts_domain(self):
        locator = ServerLocator("example.com")
        self.assertEqual(locator.domain, "example.com")
        self.assertIsNone(locator.port)
        self.assertIsNone(locator.location)
        self.assertTrue(
            locator.secure_connection,
            "Connections should be secure by default"
        )

    def test_initializer_rejects_empty_domain(self):
        with self.assertRaises(ValueError) as raised:
            ServerLocator("")

        self.assertIn(
            "Argument 'domain' must not be an empty string",
            str(raised.exception)
        )

    def test_initializer_rejects_none_domain(self):
        with self.assertRaises(TypeError):
            ServerLocator(None) # pyright: ignore[reportArgumentType]

    def test_port_property_can_be_set(self):
        locator = ServerLocator("example.com")
        locator.port = 8080
        self.assertEqual(locator.port, 8080)

    def test_port_property_accepts_none(self):
        locator = ServerLocator("example.com")
        locator.port = 8080
        locator.port = None
        self.assertIsNone(locator.port)

    def test_port_property_rejects_invalid_type(self):
        locator = ServerLocator("example.com")
        with self.assertRaises(TypeError):
            locator.port = "8080" # pyright: ignore[reportAttributeAccessIssue]

    def test_location_property_can_be_set(self):
        locator = ServerLocator("example.com")
        locator.location = "/api/v1"
        self.assertEqual(locator.location, "/api/v1")

    def test_location_property_accepts_none(self):
        locator = ServerLocator("example.com")
        locator.location = "/api"
        locator.location = None
        self.assertIsNone(locator.location)

    def test_location_property_rejects_invalid_type(self):
        locator = ServerLocator("example.com")
        with self.assertRaises(TypeError):
            locator.location = 123  # pyright: ignore

    def test_secure_connection_property_can_be_set(self):
        locator = ServerLocator("example.com")
        self.assertTrue(locator.secure_connection)
        locator.secure_connection = False
        self.assertFalse(locator.secure_connection)

    def test_secure_connection_property_rejects_invalid_type(self):
        locator = ServerLocator("example.com")
        with self.assertRaises(TypeError):
            locator.secure_connection = "yes" # type: ignore

    def test_str_representation(self):
        locator = ServerLocator("example.com")
        locator.port = 8080
        str_repr = str(locator)
        self.assertIn("example.com", str_repr)
        self.assertIn("8080", str_repr)
        self.assertIn("secure=True", str_repr)

    def test_repr_representation(self):
        locator = ServerLocator("example.com")
        repr_str = repr(locator)
        self.assertIn("ServerLocator", repr_str)
        self.assertIn("example.com", repr_str)


class TestLoadServerLocator(TestCase, ConfigurationFixture):
    """Tests the `load_server_locator()` function."""

    def setUp(self):
        super().setUp()
        self.user_config = self.configuration_user
        self.user_config_server_section = self.user_config.get_section(
            UserConfiguration.SERVER
        )
        self.project_config = self.configuration_project
        self.project_config_server_section = self.project_config.get_section(
            ProjectConfiguration.SERVER
        )

    def test_loads_from_cli_https_url(self):
        args = ArgumentsCLI(server="https://fathom.example.com")
        locator = load_server_locator(args, Configuration(), Configuration())
        self.assertEqual(locator.domain, "fathom.example.com")
        self.assertTrue(locator.secure_connection)
        self.assertIsNone(locator.port)
        self.assertIsNone(locator.location)

    def test_loads_from_cli_http_url(self):
        args = ArgumentsCLI(server="http://fathom.example.com")
        locator = load_server_locator(args, Configuration(), Configuration())
        self.assertEqual(locator.domain, "fathom.example.com")
        self.assertFalse(locator.secure_connection)
        self.assertIsNone(locator.port)
        self.assertIsNone(locator.location)

    def test_loads_from_cli_with_port(self):
        args = ArgumentsCLI(server="https://fathom.example.com:8443")
        locator = load_server_locator(args, Configuration(), Configuration())
        self.assertEqual(locator.domain, "fathom.example.com")
        self.assertEqual(locator.port, 8443)
        self.assertTrue(locator.secure_connection)

    def test_loads_from_cli_with_path(self):
        args = ArgumentsCLI(server="https://fathom.example.com/api/v1")
        locator = load_server_locator(args, Configuration(), Configuration())
        self.assertEqual(locator.domain, "fathom.example.com")
        self.assertEqual(locator.location, "/api/v1")
        self.assertTrue(locator.secure_connection)

    def test_loads_from_cli_with_port_and_path(self):
        args = ArgumentsCLI(
            server="https://fathom.example.com:8443/api/v1"
        )
        locator = load_server_locator(args, Configuration(), Configuration())
        self.assertEqual(locator.domain, "fathom.example.com")
        self.assertEqual(locator.port, 8443)
        self.assertEqual(locator.location, "/api/v1")
        self.assertTrue(locator.secure_connection)

    def test_loads_from_cli_with_ip_address(self):
        args = ArgumentsCLI(server="http://192.168.1.100:8080")
        locator = load_server_locator(args, Configuration(), Configuration())
        self.assertEqual(locator.domain, "192.168.1.100")
        self.assertEqual(locator.port, 8080)
        self.assertFalse(locator.secure_connection)

    def test_rejects_unsupported_protocol(self):
        args = ArgumentsCLI(server="ftp://fathom.example.com")
        with self.assertRaises(InvalidConfigurationException) as raised:
            load_server_locator(args, Configuration(), Configuration())

        self.assertIn("Not a valid server location", str(raised.exception))

    def test_cli_overrides_config_values(self):
        args = ArgumentsCLI(server="http://cli.example.com:9000")
        locator = load_server_locator(
            args,
            self.user_config,
            self.project_config
        )
        self.assertEqual(locator.domain, "cli.example.com")
        self.assertEqual(locator.port, 9000)
        self.assertFalse(locator.secure_connection)

    def test_loads_from_user_config(self):
        locator = load_server_locator(
            ArgumentsCLI(),
            self.user_config,
            self.project_config
        )
        self.assertEqual(locator.domain, "localhost")
        self.assertFalse(locator.secure_connection)
        self.assertEqual(locator.port, 8080)
        self.assertIsNone(locator.location)

    def test_project_domain_overrides_user_domain(self):
        self.project_config_server_section.set_value(
            ProjectConfiguration.SERVER.DOMAIN,
            "project.example.com"
        )
        locator = load_server_locator(
            ArgumentsCLI(),
            self.user_config,
            self.project_config
        )
        self.assertEqual(locator.domain, "project.example.com")

    def test_loads_port_from_user_config(self):
        self.user_config_server_section.set_value(
            UserConfiguration.SERVER.PORT,
            8081
        )
        locator = load_server_locator(
            ArgumentsCLI(),
            self.user_config,
            self.project_config
        )
        self.assertEqual(locator.port, 8081)

    def test_loads_location_from_user_config(self):
        self.user_config_server_section.set_value(
            UserConfiguration.SERVER.LOCATION,
            "/api/v2"
        )
        locator = load_server_locator(
            ArgumentsCLI(),
            self.user_config,
            self.project_config
        )
        self.assertEqual(locator.location, "/api/v2")

    def test_loads_transport_secure_from_user_config(self):
        self.user_config_server_section.set_value(
            UserConfiguration.SERVER.TRANSPORT_SECURE,
            True
        )
        locator = load_server_locator(
            ArgumentsCLI(),
            self.user_config,
            self.project_config
        )
        self.assertTrue(locator.secure_connection)

    def test_defaults_to_secure_when_not_specified(self):
        self.user_config_server_section.remove(
            UserConfiguration.SERVER.TRANSPORT_SECURE,
        )
        locator = load_server_locator(
            ArgumentsCLI(),
            self.user_config,
            self.project_config
        )
        self.assertTrue(locator.secure_connection)

    def test_raises_error_when_server_not_found_in_user_config(self):
        self.project_config_server_section.set_value(
            ProjectConfiguration.SERVER.NAME,
            "nonexistent"
        )
        with self.assertRaises(InvalidConfigurationException) as raised:
            load_server_locator(
                ArgumentsCLI(),
                self.user_config,
                self.project_config
            )

        self.assertIn("Missing configuration", str(raised.exception))

    def test_raises_error_when_domain_missing(self):
        user_config = Configuration()
        server_section = ConfigurationSection(UserConfiguration.SERVER)
        server_section.set_value(
            UserConfiguration.SERVER.NAME,
            "Test Server"
        )
        user_config.add_section(server_section)
        with self.assertRaises(InvalidConfigurationException) as raised:
            load_server_locator(
                ArgumentsCLI(),
                user_config,
                self.project_config
            )

        self.assertIn(
            "Missing configuration in user config",
            str(raised.exception)
        )

    def test_loads_all_properties_from_combined_configs(self):
        self.user_config_server_section.set_value(
            UserConfiguration.SERVER.PORT,
            8443
        )
        self.user_config_server_section.set_value(
            UserConfiguration.SERVER.LOCATION,
            "/api"
        )
        self.user_config_server_section.set_value(
            UserConfiguration.SERVER.TRANSPORT_SECURE,
            False
        )
        self.project_config_server_section.set_value(
            ProjectConfiguration.SERVER.DOMAIN,
            "project.example.com"
        )

        locator = load_server_locator(
            ArgumentsCLI(),
            self.user_config,
            self.project_config
        )

        self.assertEqual(locator.domain, "project.example.com")
        self.assertEqual(locator.port, 8443)
        self.assertEqual(locator.location, "/api")
        self.assertFalse(locator.secure_connection)

    def test_multiple_server_sections_selects_correct_one(self):
        another_server = ConfigurationSection(
            UserConfiguration.SERVER,
            sequence_number=2
        )
        another_server.set_value(
            UserConfiguration.SERVER.NAME,
            "development"
        )
        another_server.set_value(
            UserConfiguration.SERVER.DOMAIN,
            "dev.example.com"
        )
        self.user_config.add_section(another_server)

        locator = load_server_locator(
            ArgumentsCLI(),
            self.user_config,
            self.project_config
        )
        self.assertEqual(locator.domain, "localhost")

        # Change project to reference development server
        self.project_config_server_section.set_value(
            ProjectConfiguration.SERVER.NAME,
            "development"
        )
        locator = load_server_locator(
            ArgumentsCLI(),
            self.user_config,
            self.project_config
        )
        self.assertEqual(locator.domain, "dev.example.com")


if __name__ == "__main__":
    TestCase.run_tests()
