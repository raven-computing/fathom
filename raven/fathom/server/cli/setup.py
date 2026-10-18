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

from raven.fathom.base import InputPrompt, User
from raven.fathom.base import SecretToken
from raven.fathom.base.context import APPLICATION_NAME
from raven.fathom.server.cli.command import ServerCommand
from raven.fathom.server.core.logging import Logger, log_stdout
from raven.fathom.server.models import Settings
from raven.fathom.server.security import UserAuthenticator
from raven.fathom.server.core.user_management import SYSTEM_USER_IDENTIFIER
from raven.fathom.server.core.user_management import UserManager


LOG = Logger.get()

def _validate_organisation_name(name: str) -> bool:
    if len(name) > 0:
        return True

    LOG.i("Organisation name must not be empty")
    return False


def _validate_password(password: str) -> bool:
    if len(password) > 0:
        return True

    LOG.i("Password must not be empty")
    return False


class SetupCommand(ServerCommand):
    """Implementation of the `setup` server command."""

    def execute(self) -> int:
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
            validator=_validate_organisation_name
        )

        LOG.i("")
        LOG.i("The server application needs to create a superuser account.")
        LOG.i(
            "This user is used to authenticate local administrative commands "
            "submitted via the CLI."
        )
        LOG.i(
            "You will now be asked to create a password "
            "for that system user."
        )
        while True:
            LOG.i("")
            LOG.i(
                "Setting password for system user '%s'.",
                SYSTEM_USER_IDENTIFIER
            )
            password = prompt.read(
                "Password: ",
                secret=True,
                validator=_validate_password
            )

            confirmation = prompt.read(
                "Confirm password: ",
                secret=True,
                validator=_validate_password
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
            default_secret_size=16
            shared_secret = SecretToken(size=default_secret_size).to_string()
            LOG.i("Generated shared secret:")
            log_stdout("")
            log_stdout(f"       o{'-' * (default_secret_size+2)}o")
            log_stdout(f"       | {shared_secret} |")
            log_stdout(f"       o{'-' * (default_secret_size+2)}o")
            log_stdout("")
            LOG.i("Please store it in a secure place.")

        user = User(
            identifier="",
            password=password,
        )
        LOG.i("")
        LOG.i("Setting system user '%s'.", SYSTEM_USER_IDENTIFIER)
        UserManager(UserAuthenticator()).create_system_user(user)
        LOG.i("Creating organisation settings for '%s'", organisation_name)
        Settings.create(
            organisation_name=organisation_name,
            shared_secret=shared_secret,
            active=True,
        )
        LOG.i("Server setup completed")
        LOG.i("You may now start the server")
        return 0
