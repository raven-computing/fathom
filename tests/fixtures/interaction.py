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
"""Test fixtures for client-server interaction data structures."""

import base64
import json

from datetime import datetime

from raven.fathom.base import ClientRequest, Interaction, ServerResponse
from raven.fathom.base import ClientDeploymentIntent
from raven.fathom.base import DeploymentAuthorization, DeploymentMessage
from raven.fathom.base import Package
from raven.fathom.base.parcel import PARCEL_TEXT_ENCODING
from raven.fathom.base.parcel import PACKAGE_BYTES_ENCODING

from tests.fixtures.project import ProjectFixture
from tests.fixtures.package import PackageFixture
from tests.fixtures.user import UserFixture

# pyright: reportOptionalMemberAccess=false


class ClientServerInteractionFixture(
    ProjectFixture, UserFixture, PackageFixture
):
    """Test fixture to set up client request objects."""

    @property
    def client_request_deployment_request(self) -> ClientRequest:
        """A `ClientRequest` object with `Interaction.REQUEST_DEPLOYMENT`."""
        req = ClientRequest(Interaction.REQUEST_DEPLOYMENT)
        req.project = self.project
        req.deployment_intent = ClientDeploymentIntent()
        req.deployment_intent.project = req.project
        req.deployment_intent.overwrite_existing = False
        return req

    @property
    def client_request_deployment_request_encoded(self) -> dict:
        """A dictionary representation of
        the `client_request_deployment_request` property.
        """
        request = self.client_request_deployment_request
        return {
            "action": str(request.action),
            "project": {
                "identifier": request.project.identifier,
                "name": request.project.name,
                "description": request.project.description,
                "version": {
                    "identifier": request.project.version.identifier,
                    "isLatest": False,
                },
            },
            "intent": {
                "type": "deployment",
                "overwriteExisting": (
                    request.deployment_intent.overwrite_existing
                ),
            }
        }

    @property
    def client_request_deployment_request_encoded_json(self) -> str:
        """A JSON representation of
        the `client_request_deployment_request` property.
        """
        return self.encode_to_json_string(
            self.client_request_deployment_request_encoded
        )

    @property
    def server_response_deployment_request(self) -> ServerResponse:
        """A `ServerResponse` object with `Interaction.REQUEST_DEPLOYMENT`.

        The deployment authorization of the response is granted.
        """
        resp = ServerResponse(Interaction.REQUEST_DEPLOYMENT)
        resp.deployment_authorization = DeploymentAuthorization.grant(
            self.client_request_deployment_request.deployment_intent,
            "test-secret-token",
            datetime.max.replace(microsecond=0),
        )
        return resp

    @property
    def server_response_deployment_request_encoded(self) -> dict:
        """A dictionary representation of the
        `server_response_deployment_request` property.
        """
        response = self.server_response_deployment_request
        auth = response.deployment_authorization
        return {
            "action": str(response.action),
            "deploymentAuthorization": {
                "isGranted": True,
                "token": auth.token,
                "expirationTime": auth.expiration_time.isoformat(
                    timespec="seconds"
                ),
            },
        }

    @property
    def server_response_deployment_request_encoded_json(self) -> str:
        """A JSON representation of
        the `server_response_deployment_request` property.
        """
        return self.encode_to_json_string(
            self.server_response_deployment_request_encoded
        )

    @property
    def client_request_deployment_transaction(self) -> ClientRequest:
        """A `ClientRequest` object with `Interaction.TRANSACT_DEPLOYMENT`."""
        req = ClientRequest(Interaction.TRANSACT_DEPLOYMENT)
        req.deployment_authorization = DeploymentAuthorization.grant(
            self.client_request_deployment_request.deployment_intent,
            "test-secret-token",
            datetime.max.replace(microsecond=0),
        )
        req.package = self.packed_package
        return req

    @property
    def client_request_deployment_transaction_encoded(self) -> dict:
        """A dictionary representation of
        the `client_request_deployment_transaction` property.
        """
        request = self.client_request_deployment_transaction
        return {
            "action": str(Interaction.TRANSACT_DEPLOYMENT),
            "deploymentAuthorization": {
                "token": request.deployment_authorization.token,
            },
            "package": {
                "format": str(Package.TransportFormat.ARCHIVE_ZIP),
                "encoding": PACKAGE_BYTES_ENCODING,
                "data": base64.b64encode(
                    request.package.get_bytes()
                ).decode(PARCEL_TEXT_ENCODING),
            },
        }

    @property
    def client_request_deployment_transaction_encoded_json(self) -> str:
        """A JSON representation of
        the `client_request_deployment_transaction` property.
        """
        return self.encode_to_json_string(
            self.client_request_deployment_transaction_encoded
        )

    @property
    def server_response_deployment_transaction(self) -> ServerResponse:
        """A `ServerResponse` object with `Interaction.TRANSACT_DEPLOYMENT`."""
        resp = ServerResponse(Interaction.TRANSACT_DEPLOYMENT)
        resp.deployment_message = DeploymentMessage(
            is_successful=True,
            message="Deployment completed successfully.",
        )
        return resp

    @property
    def server_response_deployment_transaction_encoded(self) -> dict:
        """A dictionary representation of the
        `server_response_deployment_transaction` property.
        """
        response = self.server_response_deployment_transaction
        return {
            "action": str(response.action),
            "deploymentResult": {
                "isSuccessful": response.deployment_message.is_successful,
                "message": response.deployment_message.message,
            },
        }

    @property
    def server_response_deployment_transaction_encoded_json(self) -> str:
        """A JSON representation of
        the `server_response_deployment_transaction` property.
        """
        return self.encode_to_json_string(
            self.server_response_deployment_transaction_encoded
        )


    def encode_to_json_string(self, data: dict) -> str:
        """Encodes a dictionary to a JSON string."""
        return json.dumps(data, indent=2)

    def encode_to_json_bytes(self, data: dict) -> bytes:
        """Encodes a dictionary to a JSON byte string."""
        return json.dumps(data, indent=2).encode(PARCEL_TEXT_ENCODING)

    def decode_from_json_string(self, encoded: str) -> dict:
        """Decodes a JSON string to a dictionary."""
        return json.loads(encoded)

    def decode_from_json_bytes(self, encoded: bytes) -> dict:
        """Decodes a JSON byte string to a dictionary."""
        return json.loads(encoded.decode(PARCEL_TEXT_ENCODING))
