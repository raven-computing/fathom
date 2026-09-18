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
"""Functionality tests for the CLI help arguments.

We want to test the output format because we have custom handling
of the help argument. Since the `argparse.ArgumentParser` from the stdlib
is used internally by the Fathom `parse_args()` function and that is
not unit-testable, this is a functionality test case.
"""

from tests.functionality import TestCase

from raven.fathom.server.cli import ExitStatus


# pylint: disable=invalid-name


EXPECTED_CLIENT_HELP_OUTPUT = """\
usage: fathom [options] <COMMAND> ...

Interact with a Fathom server.

positional arguments:
  <COMMAND>
    deploy             Deploy project documentation resources.

    manage             Manage a Fathom server remotely. Usage of this command requires the user to
                       have administrative privileges.

    setup              Perform a setup action.

options:
  --debug              Turn on debug logging.

  --password PASSWORD  The password to use for authentication. If this option is used, the
                       application will not prompt the user to enter a password on the command-line.
                       If you intend to use this option in a non-development environment, it is
                       recommended that you instruct your shell to not store the entered command in
                       its history so that the password is not exposed. Consider passing the
                       password via the FATHOM_CLIENT_PASSWORD environment variable instead.

  --quiet              Turn off all output except errors.

  --server SERVER      The URL of the Fathom server to connect to. For example, to connect to a
                       local server running on port 8080, use 'http://localhost:8080' as the option
                       value.

  --user USER          The username identifier to use for authentication. Using this option you can
                       override the username that would otherwise be derived from a user
                       configuration file or the FATHOM_CLIENT_USERNAME environment variable.

  --verbose            Turn on verbose output.

  -#, --version        Show program version information and then exit.

  -?, --help           Show this help message and then exit.

[This version of the Fathom client is a Beta build]
"""


EXPECTED_SERVER_HELP_OUTPUT = """\
usage: fathom-server [options] <COMMAND> ...

Setup and manage the Fathom server application and its resources.

positional arguments:
  <COMMAND>
    setup               Perform initial setup work for the server application. This should be done
                        once after installation. This step is interactive.

    user                Manage dedicated application users. This command requires you to
                        authenticate and have administrative privileges.

    project             Manage deployable projects.

options:
  --create-default-config
                        Create the server configuration file with default values if the file does
                        not already exist at startup.

  --debug               Turn on debug logging.

  --port <PORT>         The port number on which the server will listen. The default port is 8080.

  --verbose             Turn on verbose logging.

  --working-directory <PATH>
                        The absolute path to the directory of the server application where server-
                        specific files are located.

  -#, --version         Show program version information and then exit.

  -?, --help            Show this help message and then exit.

[This version of the Fathom server is a Beta build]
"""


class TestClientHelpOptionCLI(TestCase):
    """Functionality tests for the help text that is shown by the client when
    using the `--help` or `-?` CLI option.
    """

    AUTO_START_SERVER = False

    def setUp(self):
        super().setUp()
        self.maxDiff = None

    def test_help_option_long_form(self):
        self.client.execute("--help")
        self.assertClientSuccess()
        self.assertEqual(EXPECTED_CLIENT_HELP_OUTPUT, self.client.stdout)
        self.assertEqual("", self.client.stderr)

    def test_help_option_short_form(self):
        self.client.execute("-?")
        self.assertClientSuccess()
        self.assertEqual(EXPECTED_CLIENT_HELP_OUTPUT, self.client.stdout)
        self.assertEqual("", self.client.stderr)


class TestServerHelpOptionCLI(TestCase):
    """Functionality tests for the help text that is shown by the server when
    using the `--help` or `-?` CLI option.
    """

    AUTO_START_SERVER = False

    def setUp(self):
        super().setUp()
        self.maxDiff = None

    def test_help_option_long_form(self):
        self.server.execute("--help")
        self.assertEqual(ExitStatus.SUCCESS, self.server.command_exit_status)
        self.assertEqual(EXPECTED_SERVER_HELP_OUTPUT, self.server.stdout)
        self.assertEqual("", self.server.stderr)

    def test_help_option_short_form(self):
        self.server.execute("-?")
        self.assertEqual(ExitStatus.SUCCESS, self.server.command_exit_status)
        self.assertEqual(EXPECTED_SERVER_HELP_OUTPUT, self.server.stdout)
        self.assertEqual("", self.server.stderr)


if __name__ == "__main__":
    TestCase.run_tests()
