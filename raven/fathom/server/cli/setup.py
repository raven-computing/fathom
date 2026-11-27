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
"""CLI command handling for setup actions."""

from raven.fathom.base import InputPrompt
from raven.fathom.base import SecretToken
from raven.fathom.base import log_stdout
from raven.fathom.base.context import APPLICATION_NAME
from raven.fathom.server.cli.command import ServerCommand
from raven.fathom.server.cli.status import ExitStatus
from raven.fathom.server.core.logging import Logger
from raven.fathom.server.models import Settings
from raven.fathom.server.models import SYSTEM_USER_IDENTIFIER
from raven.fathom.server.security import UserAuthenticator
from raven.fathom.server.core.user_management import UserManager


LOG = Logger.get()


def _validate_non_empty(value: str) -> bool:
    if len(value) > 0:
        return True

    LOG.i("Value must not be empty")
    return False


def _prompt_system_user_password(
    prompt: InputPrompt,
    identifier: str
) -> str:
    """Prompts interactively for the system user password and confirmation."""
    LOG.i(
        "The server also requires a local system user account for "
        "password recovery and secret rotation operations."
    )
    LOG.i(
        "This account is never accessible over the network. "
        "Its identifier is '%s'.", identifier
    )
    while True:
        LOG.i("")
        LOG.i("Please set a password for the system user '%s'.", identifier)
        password = prompt.read(
            "Password: ",
            secret=True,
            validator=_validate_non_empty
        )
        confirmation = prompt.read(
            "Confirm password: ",
            secret=True,
            validator=_validate_non_empty
        )
        if confirmation == password:
            return password

        LOG.i("Password confirmation does not match. Please try again.")


class SetupCommand(ServerCommand):
    """Implementation of the `setup` server command."""

    def execute(self) -> int:
        user_manager = UserManager(UserAuthenticator())
        if user_manager.is_setup_complete():
            LOG.i("The server has already been set up")
            return ExitStatus.FAILURE

        prompt = InputPrompt.instance()
        LOG.i(
            "Performing initial setup procedure "
            "for the %s server", APPLICATION_NAME
        )
        LOG.i("")
        LOG.i(
            "Please enter the name of the organisation "
            "that this server instance will be serving."
        )
        organisation_name = prompt.read(
            "Name: ",
            validator=_validate_non_empty
        )

        LOG.i("")
        LOG.i("Please enter the identifier for the initial administrator.")
        admin_identifier = prompt.read(
            "Administrator username: ",
            validator=_validate_non_empty
        )

        while True:
            LOG.i("")
            LOG.i("Please enter a password for '%s'.", admin_identifier)
            password = prompt.read(
                "Password: ",
                secret=True,
                validator=_validate_non_empty
            )
            confirmation = prompt.read(
                "Confirm password: ",
                secret=True,
                validator=_validate_non_empty
            )
            if confirmation == password:
                break

            LOG.i("Password confirmation does not match. Please try again.")

        LOG.i("")
        LOG.i(
            "Define a shared secret that users must provide when signing up."
        )
        LOG.i("(Press enter to automatically generate one)")
        shared_secret = prompt.read("Secret: ", secret=True)
        if not shared_secret:
            default_secret_size = 16
            shared_secret = SecretToken(size=default_secret_size).to_string()
            LOG.i("Generated shared secret:")
            log_stdout("")
            log_stdout(f"       o{'-' * (default_secret_size+2)}o")
            log_stdout(f"       | {shared_secret} |")
            log_stdout(f"       o{'-' * (default_secret_size+2)}o")
            log_stdout("")
            LOG.i("Please store it in a secure place.")

        LOG.i("")
        LOG.i("Creating organisation settings for '%s'", organisation_name)
        Settings.create(
            organisation_name=organisation_name,
            shared_secret=shared_secret,
            active=True,
        )
        LOG.i("Creating initial administrator '%s'", admin_identifier)
        user_manager.create_initial_admin(admin_identifier, password)

        LOG.i("")
        system_password = _prompt_system_user_password(
            prompt, SYSTEM_USER_IDENTIFIER
        )
        LOG.i("")
        LOG.i("Creating system user '%s'", SYSTEM_USER_IDENTIFIER)
        user_manager.create_system_user(SYSTEM_USER_IDENTIFIER, system_password)
        LOG.i("Server setup completed")
        LOG.i("You may now start the server")
        return ExitStatus.SUCCESS
