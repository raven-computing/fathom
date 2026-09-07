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
"""Defines serializable parcel types for client requests
and server responses.
"""

import json
import base64

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, TypeVar, Optional, Union

from raven.fathom.base.interaction import ClientRequest, ServerResponse
from raven.fathom.base.interaction import Interaction
from raven.fathom.base.interaction import ResponseMessage
from raven.fathom.base.deployment import ClientDeploymentIntent
from raven.fathom.base.deployment import DeploymentAuthorization
from raven.fathom.base.deployment import DeploymentMessage
from raven.fathom.base.project import Project, ProjectVersion
from raven.fathom.base.user import User, UserState
from raven.fathom.base.package import Package, PackageOperationException
from raven.fathom.base.typing import TypeCheck
from raven.fathom.base.exceptions import FathomBaseException


class ParcelException(FathomBaseException):
    """Base exception class for all parcel-related exceptions."""


class ParcelEncodingException(ParcelException):
    """An exception raised when a `Parcel` object cannot be encoded."""


class ParcelDecodingException(ParcelException):
    """An exception raised when a `Parcel` object cannot be decoded."""


class ParcelValidationException(ParcelException):
    """An exception raised by `ParcelValidator` instances to indicate
    a failed parcel validation.
    """


class Parcel(ABC):
    """A serializable entity."""

    @abstractmethod
    def content_type(self) -> str:
        """Gets the content type applicable for this parcel.

        Returns:
            str: The content type of this parcel, e.g. "application/json".
        """

    @abstractmethod
    def encode(self) -> bytes:
        """Encodes this parcel into a series of bytes.

        Returns:
            bytes: The encoded bytes of this parcel.

        Raises:
            ParcelEncodingException: If the encoding fails.
            ParcelValidationException: If the parcel cannot be validated.
        """

    @abstractmethod
    def decode(self) -> Any:
        """Decodes this parcel into an object.

        Returns:
            Any: The decoded object of this parcel.

        Raises:
            ParcelDecodingException: If the decoding fails.
            ParcelValidationException: If the parcel cannot be validated.
        """


T = TypeVar("T")


class ParcelValidator(ABC):
    """A validator for Parcel encodings."""

    @abstractmethod
    def validate(self, parcel: T) -> T:
        """Validates the specified parcel.

        Args:
            parcel (T): The parcel to validate.

        Returns:
            T: The specified parcel, may be mutated.

        Raises:
            ParcelValidationException: If the validation fails.
        """


# Constant indicating what encoding to use for serialized parcels.
PARCEL_TEXT_ENCODING = "UTF-8"

# Constant indicating what encoding to use for raw package bytes.
PACKAGE_BYTES_ENCODING = "Base64"

# Constant indicating the MIME type for JSON-encoded parcels.
MIME_TYPE_JSON = "application/json"

# Acceptable types to specify serialized forms of a request or response.
SerializedForm = Union[bytes, str]


class RequestParcelJSON(Parcel):
    """A JSON-serializable parcel representing a client request.

    Attributes:
        text_encoding (str): The unicode encoding to be used
            when encoding/decoding JSON-formatted text. Defaults to UTF-8.
    """

    def __init__(
        self,
        client_request: Union[ClientRequest, SerializedForm],
        validator: Optional[ParcelValidator] = None
    ):
        """Initializes a new `RequestParcelJSON` instance.

        Args:
            client_request (ClientRequest | bytes | str): The request to wrap
                in a parcel. May be a `ClientRequest` object or an already
                encoded such instance as `bytes` or `str`.
            validator (ParcelValidator): An optional validator to use when
                encoding and decoding the specified request.
                May be `None` to not validate.
        """
        super().__init__()
        self.text_encoding = PARCEL_TEXT_ENCODING
        self._request = client_request
        if validator:
            TypeCheck.require_arg(validator, ParcelValidator)

        self._validator = validator

    def content_type(self):
        return MIME_TYPE_JSON

    def encode(self):
        TypeCheck.require(self._request, ClientRequest)
        try:
            self._request = self._encode_obj_structure()
        except (ValueError, TypeError, AttributeError) as error:
            raise ParcelEncodingException(
                "An unexpected error has occurred while trying to encode "
                "a client request to a JSON object"
            ) from error

        if self._validator is not None:
            self._request = self._validator.validate(self._request)

        return self._encode_json_obj()

    def decode(self) -> ClientRequest:
        TypeCheck.require(self._request, (bytes, str))
        try:
            self._request = self._decode_obj_structure()
        except (ValueError, TypeError, AttributeError) as error:
            raise ParcelDecodingException(
                "An unexpected error has occurred while trying to decode "
                "a JSON object to a client request object"
            ) from error

        if self._validator is not None:
            self._request = self._validator.validate(self._request)

        return self._create_client_request_obj()

    def _encode_obj_structure(self):
        assert isinstance(self._request, ClientRequest)
        obj = {
            "action": str(self._request.action.value),
        }
        self._encode_project(obj)
        self._encode_intent(obj)
        self._encode_deployment_authorization(obj)
        try:
            self._encode_package(obj)
        except PackageOperationException as ex:
            raise ParcelEncodingException(
                "Failed to encode package of client request"
            ) from ex

        self._encode_managed_user(obj)
        return obj

    def _decode_obj_structure(self):
        if isinstance(self._request, bytes):
            self._request = self._decode_obj_bytes()

        assert isinstance(self._request, str)
        try:
            return json.loads(self._request)
        except json.JSONDecodeError as error:
            raise ParcelDecodingException(
                "Failed to decode client request JSON string"
            ) from error

    def _create_client_request_obj(self):
        assert isinstance(self._request, dict)
        try:
            request = ClientRequest(
                Interaction(self._request.get("action"))
            )
        except ValueError as error:
            raise ParcelDecodingException(
                f"Invalid client request action encountered: {error}"
            ) from None

        request.project = self._decode_project()
        request.deployment_intent = self._decode_intent()
        if isinstance(request.deployment_intent, ClientDeploymentIntent):
            request.deployment_intent.project = request.project

        request.deployment_authorization = self._decode_deployment_auth()
        request.package = self._decode_package()
        request.managed_user = self._decode_managed_user()
        return request

    def _encode_project(self, structure):
        assert isinstance(self._request, ClientRequest)
        project = (
            self._request.project
            or (
                self._request.deployment_intent
                and self._request.deployment_intent.project
            )
        )
        if project is None:
            return

        project_struct: dict[str, Union[str, dict]] = {
            "identifier": project.identifier,
        }
        if project.name:
            project_struct["name"] = project.name

        if project.description:
            project_struct["description"] = project.description

        if project.version:
            project_struct["version"] = {
                "identifier": project.version.identifier,
                "isLatest": project.version.is_latest,
            }

        structure["project"] = project_struct

    def _encode_intent(self, structure):
        assert isinstance(self._request, ClientRequest)
        intent = self._request.deployment_intent
        if intent is not None:
            structure["intent"] = {
                "type": "deployment",
                "overwriteExisting": intent.overwrite_existing,
            }

    def _encode_deployment_authorization(self, structure):
        assert isinstance(self._request, ClientRequest)
        auth = self._request.deployment_authorization
        if auth is not None:
            structure["deploymentAuthorization"] = {
                "token": auth.token,
            }

    def _decode_project(self):
        assert isinstance(self._request, dict)
        project_struct = self._request.get("project")
        if project_struct is None:
            return None

        assert isinstance(project_struct, dict)
        identifier = project_struct.get("identifier")
        assert isinstance(identifier, str)
        project = Project(identifier)
        project.name = project_struct.get("name", "")
        project.description = project_struct.get("description", "")
        version_struct = project_struct.get("version")
        if version_struct is not None:
            version = ProjectVersion(version_struct.get("identifier"))
            version.is_latest = version_struct.get("isLatest", False)
            project.version = version

        return project

    def _decode_intent(self):
        assert isinstance(self._request, dict)
        intent_struct = self._request.get("intent")
        if intent_struct is None:
            return None

        assert isinstance(intent_struct, dict)
        intent = None
        if intent_struct.get("type", "deployment") == "deployment":
            intent = ClientDeploymentIntent()
            oe = intent_struct.get("overwriteExisting")
            if oe is not None:
                intent.overwrite_existing = oe

        return intent

    def _decode_deployment_auth(self):
        assert isinstance(self._request, dict)
        auth_struct = self._request.get("deploymentAuthorization")
        if auth_struct is None:
            return None

        assert isinstance(auth_struct, dict)
        # Only the token is relevant for requests
        token = auth_struct.get("token")
        return DeploymentAuthorization(
            status=DeploymentAuthorization.Status.UNSPECIFIED,
            intent=None,
            token=token,
            expiration_time=None,
        )

    def _encode_package(self, structure):
        assert isinstance(self._request, ClientRequest)
        package = self._request.package
        if package is None:
            return

        structure["package"] = {
            "format": str(package.transport_format),
            "encoding": PACKAGE_BYTES_ENCODING,
            "data": self._encode_package_data()
        }

    def _decode_package(self):
        assert isinstance(self._request, dict)
        package_struct = self._request.get("package")
        if package_struct is None:
            return None

        assert isinstance(package_struct, dict)
        encoding = package_struct.get("encoding", "")
        if encoding != PACKAGE_BYTES_ENCODING:
            raise ParcelDecodingException(
                "Failed to decode client request package: "
                f"Unsupported data encoding '{encoding}'"
            )

        package_format = Package.TransportFormat(
            package_struct.get("format", "")
        )
        package_data = package_struct.get("data")
        if package_data is None:
            raise ParcelDecodingException(
                "Failed to decode client request package: "
                "No data specified"
            )

        package_data = self._decode_package_data(package_data)
        package = Package(package_data)
        package.transport_format = package_format
        return package

    def _encode_managed_user(self, structure):
        assert isinstance(self._request, ClientRequest)
        user = self._request.managed_user
        if user is None:
            return

        user_struct: dict[str, Union[str, bool]] = {
            "identifier": user.identifier,
        }
        if user.name:
            user_struct["name"] = user.name

        if user.is_admin:
            user_struct["isAdmin"] = user.is_admin

        if user.password:
            user_struct["password"] = user.password

        user_struct["state"] = str(user.state)

        structure["managedUser"] = user_struct

    def _decode_managed_user(self):
        assert isinstance(self._request, dict)
        user_struct = self._request.get("managedUser")
        if user_struct is None:
            return None

        assert isinstance(user_struct, dict)
        return User(
            identifier=user_struct.get("identifier", ""),
            name=user_struct.get("name", ""),
            password=user_struct.get("password", ""),
            is_admin=bool(user_struct.get("isAdmin", False)),
            state=UserState(user_struct.get("state", UserState.ACTIVE)),
        )

    def _encode_package_data(self):
        assert isinstance(self._request, ClientRequest)
        package = self._request.package
        assert package is not None
        if package.state != Package.State.PACKED:
            package.pack()

        try:
            return base64.b64encode(
                package.get_bytes()
            ).decode(self.text_encoding)
        except UnicodeEncodeError as error:
            raise ParcelEncodingException(
                "Failed to encode client request package to Base64-encoded "
                f"string of unicode encoding '{self.text_encoding}'"
            ) from error

    def _decode_package_data(self, data):
        try:
            return base64.b64decode(data)
        except ValueError as error:
            raise ParcelDecodingException(
                "Failed to decode client request package "
                "from Base64-encoded string"
            ) from error

    def _encode_json_obj(self):
        assert isinstance(self._request, dict)
        try:
            return json.dumps(self._request).encode(self.text_encoding)
        except UnicodeEncodeError as error:
            raise ParcelEncodingException(
                "Failed to encode client request structure to serialized "
                f"JSON string of unicode encoding '{self.text_encoding}'"
            ) from error
        except (ValueError, TypeError) as error:
            raise ParcelEncodingException(
                "Failed to encode client request object to JSON string"
            ) from error

    def _decode_obj_bytes(self):
        assert isinstance(self._request, bytes)
        try:
            return self._request.decode(self.text_encoding)
        except UnicodeDecodeError as error:
            raise ParcelDecodingException(
                "Failed to decode client request raw bytes "
                f"with unicode encoding '{self.text_encoding}'"
            ) from error


class ResponseParcelJSON(Parcel):
    """A JSON-serializable parcel representing a server response.

    Attributes:
        text_encoding (str): The unicode encoding to be used
            when encoding/decoding JSON-formatted text. Defaults to UTF-8.
    """

    def __init__(
        self,
        server_response: Union[ServerResponse, SerializedForm],
        validator: Optional[ParcelValidator] = None
    ):
        """Initializes a new `ResponseParcelJSON` instance.

        Args:
            server_response (ServerResponse | bytes | str): The response to
                wrap in a parcel. May be a `ServerResponse` object or an
                already encoded such instance as `bytes` or `str`.
            validator (ParcelValidator): An optional validator to use when
                encoding and decoding the specified response.
                May be `None` to not validate.
        """
        super().__init__()
        self.text_encoding = PARCEL_TEXT_ENCODING
        self._response = server_response
        if validator:
            TypeCheck.require_arg(validator, ParcelValidator)

        self._validator = validator

    def content_type(self):
        return MIME_TYPE_JSON

    def encode(self):
        TypeCheck.require(self._response, ServerResponse)
        try:
            self._response = self._encode_obj_structure()
        except (ValueError, TypeError, AttributeError) as error:
            raise ParcelEncodingException(
                "An unexpected error has occurred while trying to encode "
                "a server response to a JSON object"
            ) from error

        if self._validator is not None:
            self._response = self._validator.validate(self._response)

        return self._encode_json_obj()

    def decode(self) -> ServerResponse:
        TypeCheck.require(self._response, (bytes, str))
        try:
            self._response = self._decode_obj_structure()
        except (ValueError, TypeError, AttributeError) as error:
            raise ParcelDecodingException(
                "An unexpected error has occurred while trying to decode "
                "a JSON object to a server response object"
            ) from error

        if self._validator is not None:
            self._response = self._validator.validate(self._response)

        return self._create_server_response_obj()

    def _encode_obj_structure(self):
        assert isinstance(self._response, ServerResponse)
        obj = {
            "action": str(self._response.action.value),
        }
        self._encode_error_messages(obj)
        self._encode_warning_messages(obj)
        self._encode_server_info(obj)
        self._encode_deployment_authorization(obj)
        self._encode_deployment_result(obj)
        self._encode_managed_users(obj)
        return obj

    def _decode_obj_structure(self):
        if isinstance(self._response, bytes):
            self._response = self._decode_obj_bytes()

        assert isinstance(self._response, str)
        try:
            return json.loads(self._response)
        except json.JSONDecodeError as error:
            raise ParcelDecodingException(
                "Failed to decode server response JSON string"
            ) from error

    def _create_server_response_obj(self):
        assert isinstance(self._response, dict)
        response = ServerResponse(Interaction(self._response.get("action")))
        response.errors = self._decode_error_messages() or []
        response.warnings = self._decode_warning_messages() or []
        response.server_info = self._decode_server_info()
        response.deployment_authorization = self._decode_deployment_auth()
        response.deployment_message = self._decode_deployment_result()
        response.managed_users = self._decode_managed_users()
        return response

    def _encode_error_messages(self, structure):
        assert isinstance(self._response, ServerResponse)
        if self._response.has_errors():
            structure["errors"] = [
                {"code": error.code,
                 "message": error.text}
                 for error in self._response.errors
            ]
    def _encode_warning_messages(self, structure):
        assert isinstance(self._response, ServerResponse)
        if self._response.has_warnings():
            structure["warnings"] = [
                {"code": warning.code,
                 "message": warning.text}
                 for warning in self._response.warnings
            ]

    def _encode_server_info(self, structure):
        assert isinstance(self._response, ServerResponse)
        if self._response.server_info is not None:
            structure["serverInfo"] = self._response.server_info

    def _encode_deployment_authorization(self, structure):
        assert isinstance(self._response, ServerResponse)
        auth = self._response.deployment_authorization
        if auth is not None:
            structure["deploymentAuthorization"] = {
                "isGranted": auth.is_granted(),
            }
            if auth.is_granted():
                structure["deploymentAuthorization"]["token"] = auth.token
                if auth.expiration_time is not None:
                    structure["deploymentAuthorization"]["expirationTime"] = (
                        auth.expiration_time.isoformat(
                            timespec="seconds"
                        )
                    )
            else:
                structure["deploymentAuthorization"]["statusCode"] = (
                    auth.status.code()
                )

    def _encode_deployment_result(self, structure):
        assert isinstance(self._response, ServerResponse)
        result = self._response.deployment_message
        if result is not None:
            structure["deploymentResult"] = {
                "isSuccessful": result.is_successful,
                "message": result.message,
            }

    def _encode_managed_users(self, structure):
        assert isinstance(self._response, ServerResponse)
        if self._response.managed_users is not None:
            structure["managedUsers"] = [
                {
                    "identifier": user.identifier,
                    "name": user.name,
                    "isAdmin": user.is_admin,
                    "state": str(user.state),
                }
                for user in self._response.managed_users
            ]

    def _decode_error_messages(self):
        assert isinstance(self._response, dict)
        errors = self._response.get("errors")
        if errors is None:
            return None

        assert isinstance(errors, list)
        return [
            ResponseMessage(error["code"], error["message"])
            for error in errors
        ]

    def _decode_warning_messages(self):
        assert isinstance(self._response, dict)
        warnings = self._response.get("warnings")
        if warnings is None:
            return None

        assert isinstance(warnings, list)
        return [
            ResponseMessage(warning["code"], warning["message"])
            for warning in warnings
        ]

    def _decode_server_info(self):
        assert isinstance(self._response, dict)
        info = self._response.get("serverInfo")
        if info is None:
            return None

        assert isinstance(info, dict)
        return info

    def _decode_deployment_auth(self):
        assert isinstance(self._response, dict)
        auth_struct = self._response.get("deploymentAuthorization")
        if auth_struct is None:
            return None

        assert isinstance(auth_struct, dict)
        token = auth_struct.get("token")
        expiration_time = auth_struct.get("expirationTime")
        if expiration_time is not None:
            try:
                expiration_time = datetime.fromisoformat(expiration_time)
            except ValueError as error:
                raise ParcelDecodingException(
                    "Invalid ISO-8601 timestamp format for expiration time "
                    f"value in deployment authorization: '{expiration_time}'"
                ) from error

        is_granted = auth_struct.get("isGranted", False)
        if not isinstance(is_granted, bool):
            raise ParcelDecodingException(
                "Invalid type of isGranted property in DeploymentAuthorization"
            )

        if is_granted:
            status = DeploymentAuthorization.Status.GRANTED
        else:
            status_code = auth_struct.get("statusCode")
            if status_code is not None:
                if not isinstance(status_code, int):
                    raise ParcelDecodingException(
                        "Invalid type of statusCode property "
                        "in DeploymentAuthorization"
                    )
                status = DeploymentAuthorization.Status.from_code(status_code)
            else:
                status = DeploymentAuthorization.Status.UNSPECIFIED

        auth = DeploymentAuthorization(
            status=status,
            intent=None,
            token=token,
            expiration_time=expiration_time,
        )
        return auth

    def _decode_deployment_result(self):
        assert isinstance(self._response, dict)
        res_struct = self._response.get("deploymentResult")
        if res_struct is None:
            return None

        assert isinstance(res_struct, dict)
        result = DeploymentMessage()
        result.is_successful = res_struct.get("isSuccessful", False)
        result.message = res_struct.get("message")
        return result

    def _decode_managed_users(self):
        assert isinstance(self._response, dict)
        user_structs = self._response.get("managedUsers")
        if user_structs is None:
            return None

        assert isinstance(user_structs, list)
        return [
            User(
                identifier=user_struct.get("identifier", ""),
                name=user_struct.get("name", ""),
                is_admin=bool(user_struct.get("isAdmin", False)),
                state=UserState(
                    user_struct.get("state", UserState.ACTIVE)
                ),
            )
            for user_struct in user_structs
        ]

    def _encode_json_obj(self):
        try:
            return json.dumps(self._response).encode(self.text_encoding)
        except UnicodeEncodeError as error:
            raise ParcelEncodingException(
                "Failed to encode server response structure to serialized "
                f"JSON string of unicode encoding '{self.text_encoding}'"
            ) from error
        except (ValueError, TypeError) as error:
            raise ParcelEncodingException(
                "Failed to encode server response object to JSON string"
            ) from error

    def _decode_obj_bytes(self):
        assert isinstance(self._response, bytes)
        try:
            return self._response.decode(self.text_encoding)
        except UnicodeDecodeError as error:
            raise ParcelDecodingException(
                "Failed to decode server response raw bytes "
                f"with unicode encoding '{self.text_encoding}'"
            ) from error
