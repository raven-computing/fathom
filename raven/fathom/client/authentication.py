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
"""Implements a function to retrieve client authentication details."""

from raven.fathom.base import ClientAuthentication
from raven.fathom.base import SystemEnvironment, InputPrompt
from raven.fathom.base import Configuration
from raven.fathom.client.config import UserConfiguration
from raven.fathom.client.logging import Logger
from raven.fathom.client.cli.arguments import ArgumentsCLI


LOG = Logger.get()

ENVIRONMENT_VARIABLE_USER_NAME = "FATHOM_CLIENT_USERNAME"

ENVIRONMENT_VARIABLE_USER_PASSWORD = "FATHOM_CLIENT_PASSWORD"


def _set_client_authentication(auth, username, password):
    if username:
        auth.username = username

    if password:
        auth.password = password

def _gather_from_user_configuration(
    auth: ClientAuthentication,
    config: Configuration
):
    username = config.value_of(UserConfiguration.USER.USERNAME)
    password = config.value_of(UserConfiguration.USER.PASSWORD)
    _set_client_authentication(auth, username, password)

def _gather_from_environment(
    auth: ClientAuthentication,
    environment: SystemEnvironment
):
    username = environment.get_variable(ENVIRONMENT_VARIABLE_USER_NAME)
    password = environment.get_variable(ENVIRONMENT_VARIABLE_USER_PASSWORD)
    _set_client_authentication(auth, username, password)

def _gather_from_cli_arguments(auth: ClientAuthentication, args: ArgumentsCLI):
    _set_client_authentication(auth, args.user, args.password)

def _gather_from_user_prompt(auth: ClientAuthentication, sys_in: InputPrompt):
    if not auth.username or not auth.password:
        LOG.i("Authentication is required to perform this action")
        if not auth.username:
            auth.username = sys_in.read("User: ")

        if not auth.password:
            auth.password = sys_in.read("Password: ", secret=True)

def load_client_authentication(
    args: ArgumentsCLI,
    config: Configuration
) -> ClientAuthentication:
    """Retrieves the client authentication details.

    The searched client authentication details consist of username
    and password. This data is searched for in the following order, where
    successive individual findings may override previous ones:

    1. User configuration file
    2. Environment variables
    3. Command line arguments
    4. User input prompt

    If no username or password is found using the first three options, the
    user will be prompted interactively to enter the missing data.

    Args:
        args (ArgumentsCLI): The command line arguments. May be empty.
        config (Configuration): The user configuration. May be empty.

    Returns:
        ClientAuthentication: The loaded client authentication details.
    """
    authentication = ClientAuthentication()
    _gather_from_user_configuration(authentication, config)
    _gather_from_environment(authentication, SystemEnvironment.instance())
    _gather_from_cli_arguments(authentication, args)
    _gather_from_user_prompt(authentication, InputPrompt.instance())
    return authentication
