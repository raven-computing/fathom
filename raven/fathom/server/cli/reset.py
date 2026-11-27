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
"""CLI command handling for local administrative reset operations."""

from raven.fathom.base import InputPrompt
from raven.fathom.base import SecretToken
from raven.fathom.base import log_stdout
from raven.fathom.server.cli.command import ServerCommand
from raven.fathom.server.cli.status import ExitStatus
from raven.fathom.server.core.logging import Logger
from raven.fathom.server.core.setup import confirm_system_privileges
from raven.fathom.server.security import UserAuthenticator
from raven.fathom.server.core.user_management import UserManager


LOG = Logger.get()


def _validate_non_empty(value: str) -> bool:
    if len(value) > 0:
        return True

    LOG.i("Value must not be empty")
    return False


class ResetUserCommand(ServerCommand):
    """Implementation of the `reset user` server command.

    Resets the credentials of a managed user account. The target user is
    placed in RESET state and must re-establish their password via the
    client sign-up procedure using the current shared secret.
    """

    def execute(self) -> int:
        if not confirm_system_privileges():
            return ExitStatus.UNAUTHENTICATED

        identifier = self.args.reset_user_identifier
        LOG.i("")
        LOG.i(
            "This will reset the credentials of user '%s'.", identifier
        )
        LOG.i(
            "The user will be placed in RESET state and will not be able "
            "to log in until they complete the sign-up procedure again "
            "using the current shared secret."
        )

        manager = UserManager(UserAuthenticator())
        manager.reset_user(identifier)
        LOG.i("")
        LOG.i("Credentials for user '%s' have been reset.", identifier)
        LOG.i(
            "The user must run 'fathom setup user %s' to regain access.",
            identifier
        )
        return ExitStatus.SUCCESS


class ResetSharedSecretCommand(ServerCommand):
    """Implementation of the `reset shared-secret` server command.

    Rotates the organisation's shared signup secret. Only future sign-ups
    and pending re-signups are affected; existing active users are
    unaffected.
    """

    def execute(self) -> int:
        if not confirm_system_privileges():
            return ExitStatus.UNAUTHENTICATED

        LOG.i("")
        LOG.i(
            "This will replace the organisation's shared signup secret."
        )
        LOG.i(
            "Note: users currently in ONBOARDING or RESET state have been "
            "stamped with the previous secret. Those accounts will no longer "
            "be able to complete sign-up and must be explicitly reset again "
            "to receive the updated secret."
        )
        LOG.i(
            "Define a new shared secret that users must provide when "
            "signing up."
        )
        LOG.i("(Press enter to automatically generate one)")
        prompt = InputPrompt.instance()
        new_secret = prompt.read("New secret: ", secret=True)
        if not new_secret:
            default_secret_size = 16
            new_secret = SecretToken(size=default_secret_size).to_string()
            LOG.i("Generated shared secret:")
            log_stdout("")
            log_stdout(f"       o{'-' * (default_secret_size+2)}o")
            log_stdout(f"       | {new_secret} |")
            log_stdout(f"       o{'-' * (default_secret_size+2)}o")
            log_stdout("")
            LOG.i("Please store it in a secure place.")

        manager = UserManager(UserAuthenticator())
        manager.rotate_shared_secret(new_secret)
        LOG.i("")
        LOG.i("Shared secret has been updated successfully.")
        return ExitStatus.SUCCESS
