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
"""Structures used for deployment interactions between clients and servers.

This module defines shared data classes used during a deployment-related
interaction flow between a Fathom client and server. A deployment action starts
with a client sending a `ClientDeploymentIntent` to a server. The server
evaluates the request and returns a `DeploymentAuthorization` object, which
indicates whether the client is allowed to deploy the actual resources under
the given parameters. If the authorization is granted, the client can proceed
with the the actual deployment, which contains the deployment payload data.
The client carries out a deployment transaction with the previously obtained
authorization token. The server then processes the deployment and responds with
a `DeploymentMessage`, which contains the result of the deployment transaction.
"""

from enum import Enum
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional
from collections.abc import MutableSequence

from raven.fathom.base.project import Project
from raven.fathom.base.user import User


@dataclass
class ClientDeploymentIntent:
    """Represents the intent of a client to deploy resources.

    A deployment intent is used in a request of a client to ask a server
    whether that client is allowed to deploy resources for a given project.
    It does not contain the actual deployment payload.

    Attributes:
        user (User): The user initiating the deployment. May be `None`.
        project (Project): The project for which resources are meant to
            be deployed. May be `None`.
        overwrite_existing (bool): Whether the client intends to overwrite
            existing resources during a deployment, if applicable. This might
            require special permissions by the client. Defaults to `False`.
    """

    user: Optional[User] = None

    project: Optional[Project] = None

    overwrite_existing: bool = False


class DeploymentAuthorization:
    """An authorization which grants a package deployment to a client.

    An authorization is bound to a secret token. Only a client in possession
    of that token is granted a deployment.

    Attributes:
        status (DeploymentAuthorization.Status): The status of the
            authorization, as a `DeploymentAuthorization.Status`.
        token (str): The secret token of the authorization. May be `None`.
        expiration_time (datetime): The time of expiration of the secret token,
            if it is set. May be `None` if no token is set, otherwise
            a `datetime` must be set.
    """

    class Status(Enum):
        """The result state of an authorization."""

        GRANTED = 0, "Authorization granted"

        UNSPECIFIED = 1, "Authorization is unspecified"

        INVALID_USER = 2, "User is invalid or unknown"

        INVALID_PROJECT = (
            3, "Project is invalid, unknown or incompletely specified"
        )

        NO_PROJECT_ASSIGNED = (
            4, "User is not allowed to access requested project"
        )

        MISSING_PERM_OVERWRITE = (
            5, "User does not have permission to overwrite existing data"
        )

        EXPIRED = 6, "Authorization has expired"

        INVALID_TOKEN = 7, "Authorization token is invalid"

        def code(self) -> int:
            """The numeric code of this authorization status.

            Returns:
                int: The status code.
            """
            return self.value[0]

        def message(self) -> str:
            """The human-readable text message this authorization status.

            Returns:
                str: The status message.
            """
            return self.value[1]

        @staticmethod
        def from_code(code: int):
            """Obtains a `DeploymentAuthorization.Status` from a status code.

            Args:
                code (int): The status code to convert.

            Returns:
                Status: The corresponding status.
            """
            for status in DeploymentAuthorization.Status:
                if status.code() == code:
                    return status

            raise ValueError(f"Unknown authorization status code: {code}")

        def __repr__(self):
            stat, reason = (
                ("GRANTED", "")
                if self == DeploymentAuthorization.Status.GRANTED
                else ("DENIED", f": {self.name}")
            )
            return f"Authorization[{stat}]{reason}"

    def __init__(
        self,
        status: Status,
        intent: Optional[ClientDeploymentIntent],
        token: Optional[str],
        expiration_time: Optional[datetime],
    ):
        self._status = status
        self._granted_intent = intent
        self._token = token
        self._expiration_time = expiration_time
        self._is_granted = (
            status == DeploymentAuthorization.Status.GRANTED
            and bool(self._token)
            and bool(expiration_time)
        )

    @property
    def status(self) -> Status:
        """The authorization status, as a `DeploymentAuthorization.Status`"""
        return self._status

    @property
    def token(self) -> Optional[str]:
        """The secret token of this authorization, as a `str`.
        May be `None`.
        """
        return self._token

    @property
    def expiration_time(self) -> Optional[datetime]:
        """The time of expiration of this authorization, as a `datetime.`
        May be `None`.
        """
        return self._expiration_time

    def is_granted(self) -> bool:
        """Indicates whether this authorization is valid and granted.

        Returns:
            bool: `True` if this authorization grants a deployment.
                `False` if authorization for deployment is denied.
        """
        return self._is_granted

    def granted_parameters(self) -> Optional[ClientDeploymentIntent]:
        """Obtains the previously authorized deployment parameters.

        Returns:
            ClientDeploymentIntent: The originally authorized intent.
                Returns `None` if authorization was not granted.
        """
        if self._is_granted:
            return self._granted_intent

        return None

    def __hash__(self):
        return hash((self._status, self._token, self._expiration_time))

    def __eq__(self, obj):
        if not isinstance(obj, DeploymentAuthorization):
            return False

        return (
            self._status == obj._status
            and self._token == obj._token
            and self._expiration_time == obj._expiration_time
        )

    def __str__(self):
        return repr(self._status)

    @staticmethod
    def grant(intent, token, expiration_time):
        """Creates a granted deployment authorization."""
        return DeploymentAuthorization(
            DeploymentAuthorization.Status.GRANTED,
            intent,
            token,
            expiration_time,
        )

    @staticmethod
    def deny(status, expiration_time=None):
        """Creates a denied deployment authorization."""
        if status == DeploymentAuthorization.Status.GRANTED:
            raise ValueError(
                "Cannot create a denied authorization with granted status"
            )

        return DeploymentAuthorization(
            status,
            intent=None,
            token=None,
            expiration_time=expiration_time,
        )


@dataclass
class DeploymentMessage:
    """Represents the result of an executed deployment operation.

    A deployment message is part of the response of a server to a client
    deployment transaction request. It includes the result status of
    the deployment, an optional message and a potential list of reported
    errors and/or warnings.

    Attributes:
        is_successful (bool): Indicates whether the deployment was successful.
        message (str): An optional message providing additional information
            about the deployment.
        errors (MutableSequence): A sequence of errors encountered during
            the deployment.
        warnings (MutableSequence): A sequence of warnings generated
            during the deployment.
    """

    is_successful: bool = False

    message: Optional[str] = None

    errors: Optional[MutableSequence] = field(default_factory=list)

    warnings: Optional[MutableSequence] = field(default_factory=list)
