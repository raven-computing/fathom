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
"""Deployment autorization."""

from typing import Optional

from datetime import datetime, timedelta, timezone

from raven.fathom.base import Clock, SecretToken
from raven.fathom.base import ClientDeploymentIntent
from raven.fathom.base import DeploymentAuthorization
from raven.fathom.base import TypeCheck
from raven.fathom.base import User, Project, ProjectVersion
from raven.fathom.server.dao import DataAccess
from raven.fathom.server.models import AuthDeployment
from raven.fathom.server.models import User as StoredUser
from raven.fathom.server.models import Project as StoredProject


# Alias
_Status = DeploymentAuthorization.Status


class DeploymentAuthorizer:
    """Is responsible for authorizing Fathom deployments.

    Objects of this class process `ClientDeploymentIntent` objects as input
    and provide `DeploymentAuthorization` objects as output to indicate whether
    authorization was granted or denied. A granted authorization will contain
    a secret token which can later be supplied by a client in a subsequent
    request to carry out the actual deployment with the corresponding
    payload data. An authorization may have an expiration time after
    it was granted.
    """

    def __init__(self, clock: Clock):
        """Initializes a new `DeploymentAuthorizer` instance.

        Args:
            clock (Clock): The clock to use for determining deployment
                authorization expiration times.
        """
        TypeCheck.require_arg(clock, Clock)
        self._clock = clock
        self._ds = DataAccess.instance()

    def authorize_intent(
        self,
        intent: ClientDeploymentIntent
    ) -> DeploymentAuthorization:
        """Authorizes a deployment intent made by a client.

        The returned authorization object is either granted or denied.

        Args:
            intent (ClientDeploymentIntent): The deployment intent submitted
                by the client.

        Returns:
            DeploymentAuthorization: The authorization result of the
                requested intent.
        """
        TypeCheck.require_arg(intent, ClientDeploymentIntent)
        user = self._get_user_from_intent(intent)
        if user is None:
            return DeploymentAuthorization.deny(_Status.INVALID_USER)

        requested_project = self._get_project_from_intent(intent)
        if requested_project is None:
            return DeploymentAuthorization.deny(_Status.INVALID_PROJECT)

        if not self._is_user_assigned_to_project(user, requested_project):
            return DeploymentAuthorization.deny(_Status.NO_PROJECT_ASSIGNED)

        missing_perm_status = self._check_missing_permission_for(intent, user)
        if missing_perm_status is not None:
            return DeploymentAuthorization.deny(missing_perm_status)

        return self._grant_deployment_auth_to(intent, user, requested_project)

    def check_authorization(self, token: str) -> DeploymentAuthorization:
        """Retrieves the deployment authorization corresponding
        to the given secret token.

        Args:
            token (str): The secret token of the specific
                deployment authorization to check.

        Returns:
            DeploymentAuthorization: The previously granted deployment
                authorization associated with the given token. Returns a
                denied authorization if the token cannot be validated.
        """
        TypeCheck.require_arg(token, str)
        auth = self._ds.users().find_deployment_authorization_by_token(token)
        if auth is None:
            return DeploymentAuthorization.deny(_Status.INVALID_TOKEN)

        if self._check_is_expired(auth):
            return DeploymentAuthorization.deny(
                _Status.EXPIRED,
                auth.expiration_time
            )

        return self._create_deployment_auth_from_stored(auth)

    def _is_user_assigned_to_project(
        self,
        user: StoredUser,
        requested_project: StoredProject
    ) -> bool:
        user_assigned_projects = self._get_user_assigned_projects(user)
        return requested_project in user_assigned_projects

    def _check_missing_permission_for(
        self,
        intent: ClientDeploymentIntent,
        user: StoredUser
    ) -> Optional[_Status]:
        if intent.overwrite_existing:
            permission = self._ds.users().find_permission(user)
            if not permission.allow_overwrite:
                return _Status.MISSING_PERM_OVERWRITE

        return None

    def _check_is_expired(self, authorization: AuthDeployment) -> bool:
        expiration_time = authorization.expiration_time
        if isinstance(expiration_time, str):
            expiration_time = self._convert_str_to_datetime(expiration_time)

        TypeCheck.require(expiration_time, datetime)
        return self._clock.current_time() >= expiration_time # type: ignore

    def _convert_str_to_datetime(self, value: str) -> datetime:
        try:
            return datetime.strptime(
                value.split(".", maxsplit=1)[0], "%Y-%m-%d %H:%M:%S"
            ).replace(tzinfo=timezone.utc)
        except (TypeError, ValueError) as error:
            raise TypeError(
                "Invalid string datetime value "
                f"in stored AuthDeployment entity: '{value}'"
            ) from error

    def _create_deployment_auth_from_stored(
        self,
        auth: AuthDeployment
    ) -> DeploymentAuthorization:
        return DeploymentAuthorization.grant(
            self._granted_params_from_stored(auth),
            auth.token,
            auth.expiration_time
        )

    def _granted_params_from_stored(
        self,
        auth: AuthDeployment
    ) -> ClientDeploymentIntent:
        intent = ClientDeploymentIntent()
        intent.user = User(auth.user.identifier, auth.user.name)
        intent.project = Project(
            identifier=auth.project.identifier,
            name=auth.project.name,
            description=auth.project.description,
        )
        intent.project.version = ProjectVersion(
            identifier=str(auth.project_version),
        )
        intent.overwrite_existing = bool(auth.allow_overwrite)
        return intent

    def _grant_deployment_auth_to(
        self,
        intent: ClientDeploymentIntent,
        user: StoredUser,
        project: StoredProject
    ) -> DeploymentAuthorization:
        assert intent.project is not None
        assert intent.project.version is not None
        expiration_time = self._clock.current_time() + timedelta(minutes=5)
        auth = AuthDeployment(
            token=str(SecretToken()),
            expiration_time=expiration_time,
            user=user,
            project=project,
            project_version=intent.project.version.identifier,
            allow_overwrite=intent.overwrite_existing,
        )
        self._ds.users().create(auth)
        return self._create_deployment_auth_from_stored(auth)

    def _get_user_from_intent(
        self,
        intent: ClientDeploymentIntent
    ) -> Optional[StoredUser]:
        user_of_request = intent.user
        if user_of_request is not None:
            identifier = user_of_request.identifier
            if identifier:
                return self._ds.users().find_by_identifier(identifier)

        return None

    def _get_project_from_intent(
        self,
        intent: ClientDeploymentIntent
    ) -> Optional[StoredProject]:
        project_of_request = intent.project
        if project_of_request is not None:
            identifier = project_of_request.identifier
            version = project_of_request.version
            if identifier and version is not None:
                return self._ds.projects().find_by_identifier(identifier)

        return None

    def _get_user_assigned_projects(
        self,
        user: StoredUser
    ) -> list[StoredProject]:
        return self._ds.projects().find_all_assigned_to_user(user)
