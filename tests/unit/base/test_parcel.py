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
"""Unit tests for the base parcel module."""

import base64

from raven.fathom.base import ParcelValidator
from raven.fathom.base import RequestParcelJSON, ResponseParcelJSON
from raven.fathom.base import ParcelEncodingException
from raven.fathom.base import ParcelDecodingException
from raven.fathom.base import PackageOperationException
from raven.fathom.base import ClientRequest, Interaction, ServerResponse
from raven.fathom.base import ClientAuthentication, Package, User
from raven.fathom.base.parcel import PARCEL_TEXT_ENCODING

from tests.unit import TestCase
from tests.unit.mocks import Mock
from tests.fixtures import ClientServerInteractionFixture


# pyright: reportOptionalMemberAccess=false


class DummyValidator(ParcelValidator):
    """A dummy validator that does nothing."""

    def __init__(self):
        super().__init__()
        self.validate_called = False

    def validate(self, parcel):
        self.validate_called = True
        return parcel


class TestRequestParcelJSON(TestCase, ClientServerInteractionFixture):
    """Unit tests for the `RequestParcelJSON` class."""

    def setUp(self):
        super().setUp()
        self.validator = DummyValidator()
        self.deployment_request = self.client_request_deployment_request
        self.deployment_request_encoded = (
            self.client_request_deployment_request_encoded
        )
        self.deployment_transaction = (
            self.client_request_deployment_transaction
        )
        self.deployment_transaction_encoded = (
            self.client_request_deployment_transaction_encoded
        )

    def test_encode_deployment_request(self):
        encoded = RequestParcelJSON(self.deployment_request).encode()
        self.assertIsInstance(encoded, bytes)
        data = self.decode_from_json_bytes(encoded)
        self.assertDictEqual(data, self.deployment_request_encoded)

    def test_encode_deployment_transaction(self):
        encoded = RequestParcelJSON(self.deployment_transaction).encode()
        self.assertIsInstance(encoded, bytes)
        data = self.decode_from_json_bytes(encoded)
        self.assertDictEqual(data, self.deployment_transaction_encoded)

    def test_encode_decode_cycle(self):
        encoded = RequestParcelJSON(self.deployment_request).encode()
        self.assertIsInstance(encoded, bytes)
        decoded = RequestParcelJSON(encoded).decode()
        self.assertIsInstance(decoded, ClientRequest)
        self.assertEqual(decoded, self.deployment_request)

    def test_encode_with_validator(self):
        parcel = RequestParcelJSON(
            self.deployment_request,
            validator=self.validator
        )
        encoded = parcel.encode()
        self.assertIsInstance(encoded, bytes)
        self.assertTrue(self.validator.validate_called)

    def test_encode_missing_project(self):
        self.deployment_request.project = None
        self.deployment_request.deployment_intent.project = None
        encoded = RequestParcelJSON(self.deployment_request).encode()
        self.assertIsInstance(encoded, bytes)
        decoded = RequestParcelJSON(encoded).decode()
        self.assertIsNone(decoded.deployment_intent.project)
        self.assertIsNone(decoded.project)

    def test_encode_missing_package(self):
        self.deployment_request.package = None
        encoded = RequestParcelJSON(self.deployment_request).encode()
        self.assertIsInstance(encoded, bytes)
        decoded = RequestParcelJSON(encoded).decode()
        self.assertIsNone(decoded.package)

    def test_encode_missing_deployment_intent(self):
        self.deployment_request.deployment_intent = None
        encoded = RequestParcelJSON(self.deployment_request).encode()
        self.assertIsInstance(encoded, bytes)
        decoded = RequestParcelJSON(encoded).decode()
        self.assertIsNone(decoded.deployment_intent)

    def test_encode_missing_deployment_authorization(self):
        self.deployment_request.deployment_authorization = None
        encoded = RequestParcelJSON(self.deployment_request).encode()
        self.assertIsInstance(encoded, bytes)
        decoded = RequestParcelJSON(encoded).decode()
        self.assertIsNone(decoded.deployment_authorization)

    def test_encode_with_unicode_project_name(self):
        project_name = "A 🙂 Test Project Σ"
        self.deployment_request.project.name = project_name
        encoded = RequestParcelJSON(self.deployment_request).encode()
        self.assertIsInstance(encoded, bytes)
        decoded = RequestParcelJSON(encoded).decode()
        self.assertEqual(decoded.project.name, project_name)

    def test_encode_unpacked_package_automatically_packs_package(self):
        self.deployment_transaction.package = self.unpacked_package
        encoded = RequestParcelJSON(self.deployment_transaction).encode()
        self.assertIsInstance(encoded, bytes)
        data = self.decode_from_json_bytes(encoded)
        self.assertEqual(
            data["package"]["data"],
            base64.b64encode(
                self.packed_package.get_bytes()
            ).decode(PARCEL_TEXT_ENCODING)
        )

    def test_encode_invalid_package_raises_exception(self):
        req = self.client_request_deployment_transaction
        req.package = Mock(spec_set=Package)
        req.package.pack.side_effect = (
            PackageOperationException("Package failure")
        )
        parcel = RequestParcelJSON(req)
        with self.assertRaises(ParcelEncodingException) as raised:
            parcel.encode()

        self.assertIn(
            "Failed to encode package of client request",
            str(raised.exception)
        )

    def test_client_authentication_is_not_encoded(self):
        request = self.deployment_request
        request.authentication = ClientAuthentication("user", "password")
        encoded = RequestParcelJSON(request).encode()
        self.assertIsInstance(encoded, bytes)
        decoded = RequestParcelJSON(encoded).decode()
        self.assertIsNone(decoded.authentication)

    def test_decode_invalid_json_raises_exception(self):
        bad_bytes = b"not valid json {"
        parcel = RequestParcelJSON(bad_bytes)
        with self.assertRaises(ParcelDecodingException) as raised:
            parcel.decode()

        self.assertIn(
            "Failed to decode client request JSON string",
            str(raised.exception)
        )

    def test_decode_invalid_package_encoding_raises_exception(self):
        parcel = RequestParcelJSON(self.client_request_deployment_transaction)
        encoded = parcel.encode()
        data = self.decode_from_json_bytes(encoded)
        data["package"]["encoding"] = "Unknown"
        tampered_data = self.encode_to_json_string(data)
        tampered_parcel = RequestParcelJSON(tampered_data)
        with self.assertRaises(ParcelDecodingException) as raised:
            tampered_parcel.decode()

        self.assertIn(
            "Failed to decode client request package",
            str(raised.exception)
        )
        self.assertIn(
            "Unsupported data encoding 'Unknown'",
            str(raised.exception)
        )

    def test_decode_invalid_base64_package_raises(self):
        parcel = RequestParcelJSON(self.client_request_deployment_transaction)
        encoded = parcel.encode()
        data = self.decode_from_json_bytes(encoded)
        data["package"]["data"] = "!!!notbase64!!!"
        tampered_data = self.encode_to_json_string(data)
        tampered_parcel = RequestParcelJSON(tampered_data)
        with self.assertRaises(ParcelDecodingException) as raised:
            tampered_parcel.decode()

        self.assertIn(
            "Failed to decode client request package "
            "from Base64-encoded string",
            str(raised.exception)
        )

    def test_encode_decode_managed_user_request(self):
        request = ClientRequest(Interaction.SETUP_USER)
        request.managed_user = User(
            identifier="alpha",
            name="Alpha",
            password="secret",
            is_admin=False,
        )

        encoded = RequestParcelJSON(request).encode()
        decoded = RequestParcelJSON(encoded).decode()

        self.assertEqual(decoded.action, Interaction.SETUP_USER)
        self.assertIsNotNone(decoded.managed_user)
        assert decoded.managed_user is not None
        self.assertEqual(decoded.managed_user.identifier, "alpha")
        self.assertEqual(decoded.managed_user.name, "Alpha")
        self.assertFalse(decoded.managed_user.is_admin)
        self.assertEqual(decoded.managed_user.password, "secret")


class TestResponseParcelJSON(TestCase, ClientServerInteractionFixture):
    """Unit tests for the `ResponseParcelJSON` class."""

    def setUp(self):
        super().setUp()
        self.validator = DummyValidator()
        self.action = Interaction.REQUEST_DEPLOYMENT
        self.response_deployment_request = (
            self.server_response_deployment_request
        )
        self.response_deployment_request_encoded = (
            self.server_response_deployment_request_encoded
        )
        self.response_deployment_transaction = (
            self.server_response_deployment_transaction
        )
        self.response_deployment_transaction_encoded = (
            self.server_response_deployment_transaction_encoded
        )

    def test_encode_deployment_request_response(self):
        encoded = ResponseParcelJSON(self.response_deployment_request).encode()
        self.assertIsInstance(encoded, bytes)
        data = self.decode_from_json_bytes(encoded)
        self.assertDictEqual(data, self.response_deployment_request_encoded)

    def test_encode_deployment_transaction_response(self):
        encoded = ResponseParcelJSON(
            self.response_deployment_transaction
        ).encode()
        self.assertIsInstance(encoded, bytes)
        data = self.decode_from_json_bytes(encoded)
        self.assertDictEqual(
            data, self.response_deployment_transaction_encoded
        )

    def test_encode_decode_cycle(self):
        encoded = ResponseParcelJSON(self.response_deployment_request).encode()
        decoded = ResponseParcelJSON(encoded).decode()
        self.assertIsInstance(decoded, ServerResponse)
        self.assertEqual(decoded, self.response_deployment_request)
        encoded = ResponseParcelJSON(
            self.response_deployment_transaction
        ).encode()
        decoded = ResponseParcelJSON(encoded).decode()
        self.assertIsInstance(decoded, ServerResponse)
        self.assertEqual(decoded, self.response_deployment_transaction)

    def test_encode_with_validator(self):
        parcel = ResponseParcelJSON(
            self.response_deployment_request,
            validator=self.validator
        )
        encoded = parcel.encode()
        self.assertIsInstance(encoded, bytes)
        self.assertTrue(self.validator.validate_called)

    def test_encode_missing_errors_and_warnings(self):
        resp = ServerResponse(self.action)
        encoded = ResponseParcelJSON(resp).encode()
        data = self.decode_from_json_bytes(encoded)
        self.assertNotIn("errors", data)
        self.assertNotIn("warnings", data)

    def test_encode_missing_deployment_authorization(self):
        resp = ServerResponse(self.action)
        resp.deployment_authorization = None
        encoded = ResponseParcelJSON(resp).encode()
        data = self.decode_from_json_bytes(encoded)
        self.assertNotIn("deploymentAuthorization", data)

    def test_encode_missing_deployment_result(self):
        resp = ServerResponse(self.action)
        resp.deployment_message = None
        encoded = ResponseParcelJSON(resp).encode()
        data = self.decode_from_json_bytes(encoded)
        self.assertNotIn("deploymentResult", data)

    def test_decode_deployment_request_response(self):
        data = self.encode_to_json_string(
            self.response_deployment_request_encoded
        )
        decoded = ResponseParcelJSON(data).decode()
        self.assertIsInstance(decoded, ServerResponse)
        self.assertEqual(decoded, self.response_deployment_request)

    def test_decode_deployment_transaction_response(self):
        data = self.encode_to_json_string(
            self.response_deployment_transaction_encoded
        )
        decoded = ResponseParcelJSON(data).decode()
        self.assertIsInstance(decoded, ServerResponse)
        self.assertEqual(decoded, self.response_deployment_transaction)

    def test_decode_invalid_json_raises_exception(self):
        bad_bytes = b"not valid json {"
        parcel = ResponseParcelJSON(bad_bytes)
        with self.assertRaises(ParcelDecodingException) as raised:
            parcel.decode()

        self.assertIn(
            "Failed to decode server response JSON string",
            str(raised.exception)
        )

    def test_decode_invalid_expiration_time_raises(self):
        data = dict(self.response_deployment_request_encoded)
        data["deploymentAuthorization"]["expirationTime"] = "not-a-date"
        tampered_data = self.encode_to_json_string(data)
        parcel = ResponseParcelJSON(tampered_data)
        with self.assertRaises(ParcelDecodingException) as raised:
            parcel.decode()

        self.assertIn(
            "Invalid ISO-8601 timestamp format", str(raised.exception)
        )

    def test_decode_invalid_is_granted_type_raises(self):
        data = dict(self.response_deployment_request_encoded)
        data["deploymentAuthorization"]["isGranted"] = "yes"
        tampered_data = self.encode_to_json_string(data)
        parcel = ResponseParcelJSON(tampered_data)
        with self.assertRaises(ParcelDecodingException) as raised:
            parcel.decode()

        self.assertIn(
            "Invalid type of isGranted property", str(raised.exception)
        )

    def test_encode_decode_managed_users_response(self):
        response = ServerResponse(Interaction.LIST_USERS)
        response.managed_users = [
            User(identifier="alpha", name="Alpha", is_admin=True),
            User(identifier="user3", name="User 3", is_admin=False),
        ]

        encoded = ResponseParcelJSON(response).encode()
        decoded = ResponseParcelJSON(encoded).decode()

        self.assertEqual(decoded.action, Interaction.LIST_USERS)
        self.assertIsNotNone(decoded.managed_users)
        assert decoded.managed_users is not None
        self.assertEqual(len(decoded.managed_users), 2)
        self.assertTrue(decoded.managed_users[0].is_admin)
        self.assertFalse(decoded.managed_users[1].is_admin)


if __name__ == "__main__":
    TestCase.run_tests()
