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
"""Unit tests for authorization module."""

from datetime import datetime, timedelta, timezone

from raven.fathom.base import SecretToken, ConstantClock
from raven.fathom.base import User, Project, ProjectVersion
from raven.fathom.base import ClientDeploymentIntent, DeploymentAuthorization
from raven.fathom.base.testing import EntropySourceMock
from raven.fathom.server.dao import IncoherentDatastoreStateException
from raven.fathom.server.security import DeploymentAuthorizer, UserAuthorizer
from raven.fathom.server.models import AuthDeployment, UserPermission
from raven.fathom.server.models import User as UserModel

from tests.unit import TestCase
from tests.unit.server.mocks import DataAccessMock


class TestDeploymentAuthorizer(TestCase):
    """Unit tests for the `DeploymentAuthorizer` class."""

    def setUp(self):
        super().setUp()
        valid_user = User("test-user", "Test User")
        valid_project = Project("test-project")
        valid_project.name = "Test Project"
        valid_project.description = "A project for testing purposes"
        valid_project.version = ProjectVersion("1.2.3")
        valid_intent = ClientDeploymentIntent()
        valid_intent.user = valid_user
        valid_intent.project = valid_project
        self.valid_user = valid_user
        self.valid_project = valid_project
        self.valid_intent = valid_intent
        self._clock = ConstantClock(
            datetime(
                year=2024, month=1, day=2,
                hour=3, minute=4, second=5, microsecond=6,
                tzinfo=timezone.utc
            )
        )
        self.dao = DataAccessMock()
        self.dao.reset()
        self.dao.set_up_deployment_authorization_mocks(valid_intent)

    def get_stored_deployment_authorization(self):
        """Obtains the last stored `AuthDeployment` record."""
        mock_method = self.dao.users().create
        mock_method.assert_called_once()
        deployment_authorization = mock_method.call_args.args[0]
        self.assertIsInstance(deployment_authorization, AuthDeployment)
        found_method = self.dao.users().find_deployment_authorization_by_token
        found_method.return_value = deployment_authorization
        return deployment_authorization

    def test_authorization_without_valid_user_is_denied(self):
        intent_without_user = self.valid_intent
        intent_without_user.user = None
        auth = DeploymentAuthorizer(self._clock).authorize_intent(
            intent_without_user
        )
        self.assertFalse(auth.is_granted())
        self.assertIsNone(auth.token)
        self.assertEqual(
            auth.status, DeploymentAuthorization.Status.INVALID_USER
        )

    def test_authorization_with_unknown_user_is_denied(self):
        intent_with_unknown_user = self.valid_intent
        intent_with_unknown_user.user = User("unknown-user", "Test User")
        self.dao.users().find_by_identifier.return_value = None
        auth = DeploymentAuthorizer(self._clock).authorize_intent(
            intent_with_unknown_user
        )
        self.assertFalse(auth.is_granted())
        self.assertIsNone(auth.token)
        self.assertEqual(
            auth.status, DeploymentAuthorization.Status.INVALID_USER
        )

    def test_authorization_without_valid_project_is_denied(self):
        intent_without_project = self.valid_intent
        intent_without_project.project = None
        auth = DeploymentAuthorizer(self._clock).authorize_intent(
            intent_without_project
        )
        self.assertFalse(auth.is_granted())
        self.assertIsNone(auth.token)
        self.assertEqual(
            auth.status, DeploymentAuthorization.Status.INVALID_PROJECT
        )

    def test_authorization_with_unknown_project_is_denied(self):
        intent_unknown_project = self.valid_intent
        assert intent_unknown_project.project is not None
        intent_unknown_project.project.identifier = "unknown-project"
        self.dao.projects().find_by_identifier.return_value = None
        auth = DeploymentAuthorizer(self._clock).authorize_intent(
            intent_unknown_project
        )
        self.assertFalse(auth.is_granted())
        self.assertIsNone(auth.token)
        self.assertEqual(
            auth.status, DeploymentAuthorization.Status.INVALID_PROJECT
        )

    def test_authorization_with_valid_intent_is_granted(self):
        auth = DeploymentAuthorizer(self._clock).authorize_intent(
            self.valid_intent
        )
        self.assertTrue(auth.is_granted())
        self.assertIsNotNone(auth.token)
        self.assertEqual(
            auth.status, DeploymentAuthorization.Status.GRANTED
        )
        assert auth.token is not None
        # Validate sensitive implementation details
        self.assertRegex(
            auth.token,
            "^[a-zA-Z0-9]{32}$",
            "Implementation detail: Granted deployment authorization returned "
            "unexpected value for token. If this implementation detail was "
            "indeed changed, then please confirm by adjusting the test case."
        )
        self.assertEqual(
            auth.expiration_time,
            self._clock.current_time() + timedelta(minutes=5)
        )
        stored = self.get_stored_deployment_authorization()
        self.assertIsNotNone(stored, "Authorization should be persisted")
        self.assertEqual(stored.token, auth.token)
        self.assertEqual(auth.token, str(SecretToken()))
        self.assertEqual(stored.expiration_time, auth.expiration_time)

    def test_granted_authorizations_use_different_tokens(self):
        entropy_source = EntropySourceMock.instance()
        authorizer = DeploymentAuthorizer(self._clock)
        token_1 = authorizer.authorize_intent(self.valid_intent).token
        entropy_source.choose_sequence_index += 1
        token_2 = authorizer.authorize_intent(self.valid_intent).token
        entropy_source.choose_sequence_index += 1
        token_3 = authorizer.authorize_intent(self.valid_intent).token
        entropy_source.choose_sequence_index += 1
        # Check new instance
        token_4 = DeploymentAuthorizer(self._clock).authorize_intent(
            self.valid_intent
        ).token
        token_list = sorted(
            list(set([token_1, token_2, token_3, token_4])) # type: ignore
        )
        self.assertEqual(
            token_list, sorted(
                [token_1, token_2, token_3, token_4] # type: ignore
            )
        )

    def test_authorization_overwrite_existing_without_perm_is_denied(self):
        self.valid_intent.overwrite_existing = True
        self.dao.users().find_permission.return_value.allow_overwrite = False
        auth = DeploymentAuthorizer(self._clock).authorize_intent(
            self.valid_intent
        )
        self.assertFalse(auth.is_granted())
        self.assertIsNone(auth.token)
        self.assertEqual(
            auth.status, DeploymentAuthorization.Status.MISSING_PERM_OVERWRITE
        )

    def test_authorization_overwrite_existing_with_perm_is_granted(self):
        self.valid_intent.overwrite_existing = True
        auth = DeploymentAuthorizer(self._clock).authorize_intent(
            self.valid_intent
        )
        self.assertTrue(auth.is_granted())
        self.assertIsNotNone(auth.token)
        self.assertEqual(auth.status, DeploymentAuthorization.Status.GRANTED)

    def test_granted_authorization_token_is_validated_correctly(self):
        auth = DeploymentAuthorizer(self._clock).authorize_intent(
            self.valid_intent
        )
        stored = self.get_stored_deployment_authorization()
        auth_validated = DeploymentAuthorizer(self._clock).check_authorization(
            stored.token
        )
        self.assertIsNotNone(auth_validated)
        self.assertTrue(auth_validated.is_granted())
        self.assertEqual(auth_validated.token, auth.token)
        self.assertEqual(auth_validated.expiration_time, auth.expiration_time)

    def test_expired_authorization_token_is_denied_at_expiration_time(self):
        auth = DeploymentAuthorizer(self._clock).authorize_intent(
            self.valid_intent
        )
        stored = self.get_stored_deployment_authorization()
        assert auth.expiration_time is not None
        auth_expired = DeploymentAuthorizer(
            ConstantClock(auth.expiration_time)
        ).check_authorization(
            stored.token
        )
        self.assertIsNotNone(auth_expired)
        self.assertFalse(auth_expired.is_granted())
        self.assertIsNone(auth_expired.token)
        self.assertEqual(auth_expired.expiration_time, auth.expiration_time)
        self.assertEqual(
            auth_expired.status, DeploymentAuthorization.Status.EXPIRED
        )

    def test_expired_authorization_token_is_denied_past_expiration_time(self):
        auth = DeploymentAuthorizer(self._clock).authorize_intent(
            self.valid_intent
        )
        stored = self.get_stored_deployment_authorization()
        assert auth.expiration_time is not None
        auth_expired = DeploymentAuthorizer(
            ConstantClock(auth.expiration_time + timedelta(seconds=1))
        ).check_authorization(
            stored.token
        )
        self.assertIsNotNone(auth_expired)
        self.assertFalse(auth_expired.is_granted())
        self.assertIsNone(auth_expired.token)
        self.assertEqual(auth_expired.expiration_time, auth.expiration_time)
        self.assertEqual(
            auth_expired.status, DeploymentAuthorization.Status.EXPIRED
        )

    def test_checking_nonexistent_token_is_denied(self):
        dao = self.dao.users()
        dao.find_deployment_authorization_by_token.return_value = None
        auth = DeploymentAuthorizer(self._clock).check_authorization(
            "nonexistent-token"
        )
        self.assertFalse(auth.is_granted())
        self.assertEqual(
            auth.status,
            DeploymentAuthorization.Status.INVALID_TOKEN
        )

    def test_authorization_user_not_assigned_to_project_is_denied(self):
        self.dao.projects().find_all_assigned_to_user.return_value = []
        auth = DeploymentAuthorizer(self._clock).authorize_intent(
            self.valid_intent
        )
        self.assertFalse(auth.is_granted())
        self.assertEqual(
            auth.status,
            DeploymentAuthorization.Status.NO_PROJECT_ASSIGNED
        )


class TestAdminAuthorizer(TestCase):
    """Unit tests for the `AdminAuthorizer` class."""

    def setUp(self):
        super().setUp()
        self.dao = DataAccessMock()
        self.dao.reset()
        self.user = User("test-user", "Test User")

    def test_is_admin_returns_false_for_unknown_user(self):
        self.dao.users().find_by_identifier.return_value = None

        result = UserAuthorizer().is_administrator(self.user)
        self.assertFalse(result)

    def test_is_admin_returns_false_for_user_without_identifier(self):
        result = UserAuthorizer().is_administrator(User("", "Test User"))
        self.assertFalse(result)

    def test_is_admin_returns_false_when_permission_record_missing(self):
        stored_user = UserModel(
            identifier="test-user",
            name="Test User",
        )
        self.dao.users().find_by_identifier.return_value = stored_user
        self.dao.users().find_permission.side_effect = (
            IncoherentDatastoreStateException("missing permission")
        )

        result = UserAuthorizer().is_administrator(self.user)
        self.assertFalse(result)

    def test_is_admin_returns_false_for_regular_user(self):
        stored_user = UserModel(
            identifier="test-user",
            name="Test User",
        )
        permission = UserPermission(
            user=1,
            is_admin=False,
        )
        self.dao.users().find_by_identifier.return_value = stored_user
        self.dao.users().find_permission.return_value = permission

        result = UserAuthorizer().is_administrator(self.user)
        self.assertFalse(result)

    def test_is_admin_returns_true_for_admin_user(self):
        stored_user = UserModel(
            identifier="test-user",
            name="Test User",
        )
        permission = UserPermission(
            user=1,
            is_admin=True,
        )
        self.dao.users().find_by_identifier.return_value = stored_user
        self.dao.users().find_permission.return_value = permission

        result = UserAuthorizer().is_administrator(self.user)
        self.assertTrue(result)


if __name__ == "__main__":
    TestCase.run_tests()
